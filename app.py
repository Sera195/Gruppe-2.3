# Alle notwendigen imports
import streamlit as st
import googlemaps
import pandas as pd
import requests
from datetime import datetime

# Funktion zum Abrufen der Zugroute von Google Maps API mit einem GET-Request und festgelegter Ankunftszeit, die departure_time muss nicht angegeben werden, da sie sich aus der arrival_time ableitet
def get_train_route(api_key, start_location, end_location, arrival_time):
    # Get request von der google maps directions API
    # Quelle: https://www.youtube.com/watch?v=yOXQAmYl0Aw&t=105s
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start_location}&destination={end_location}&mode=transit&transit_mode=rail&arrival_time={arrival_time}&key={api_key}"
    response = requests.get(url)
    # Wenn der code = 200 (OK) ist, kann fortgefahren werden
    if response.status_code == 200:
        # Die Antwort wird in das json Format gebracht, um sie weiterverwenden zu können
        data = response.json()
        # Nun wird über die ausgegebenen Daten iteriert und den benötigten daten zugewiesen
        # Mit Hilfe von ChatGPT
        if "routes" in data and len(data["routes"]) > 0:
            steps = data["routes"][0]["legs"][0]["steps"]
            processed_data = []
            route_coordinates = []
            for step in steps:
                if step['travel_mode'] == 'TRANSIT':
                    departure_station = step['transit_details']['departure_stop']['name']
                    arrival_station = step['transit_details']['arrival_stop']['name']
                    # Linie entfernen, diese werden nicht benötigt, da sie nur für Tram und Buslinien angegeben ist und ansonsten leer bleibt
                    line = ""
                    departure_time = step['transit_details']['departure_time']['text']
                    arrival_time = step['transit_details']['arrival_time']['text']
                    duration = step['duration']['text']
                    route_coordinates.append((step['start_location']['lat'], step['start_location']['lng']))
                    route_coordinates.append((step['end_location']['lat'], step['end_location']['lng']))
                    processed_data.append({
                        'departure_station': departure_station,
                        'arrival_station': arrival_station,
                        'departure_time': departure_time,
                        'arrival_time': arrival_time,
                        'duration': duration
                    })
            # Zurück gegeben wird der Dataframe, welcher die wichtigsten Daten im Überblick darstellt
            return pd.DataFrame(processed_data), route_coordinates
    return None, None

# Funktion zur Umwandlung von Ortsnamen in Koordinaten, mit Hilfe der google maps geocode API
def get_coordinates(place, api_key):
    # Get request von der google maps geocode API
    # Quelle: https://www.youtube.com/watch?v=yOXQAmYl0Aw&t=105s
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            # Die Daten werden in location als Koordinate gespeichert und können im nächsten Schritt weiterverwendet werden
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
    return None, None

# Funktion zur Umwandlung von Datum und Uhrzeit in UNIX-Zeitstempel
# Da Google den UNIX-Zeitstempel verwendet und die Angabe ansonsten nicht verarbeitet werden kann
# UNIX-Zeitstempel gibt die Anzahl der Sekunden an, die seit dem 01.01.1970 vergangen sind. (https://www.confirado.de/tools/timestamp-umrechner.html#:~:text=Was%20ist%20ein%20Unix%20Timestamp,PHP%20und%20MySQL%2DDatenbanken%20ben%C3%B6tigt.)
# Mit Hilfe von https://stackoverflow.com/questions/19801727/convert-datetime-to-unix-timestamp-and-convert-it-back-in-python
def convert_to_unix_timestamp(datetime_str):
    try:
        datetime_obj = datetime.strptime(datetime_str, '%d.%m.%Y-%H:%M')
        unix_timestamp = int(datetime_obj.timestamp())-7200
        return unix_timestamp
    except ValueError:
        return None

# Hauptfunktion für die Streamlit-App
def Endroute():
    # Titel des Projekts
    st.title("TrainMeet")

    # Lesen des versteckten google maps API key aus streamlit
    # Quelle: https://www.youtube.com/watch?v=oWxAZoyyzCc
    api_key = st.secrets["auth_key"]

    # Abfrage der Abfahrtsorte, mit default Werten
    start_locations = st.text_input("""Abfahrtsorte eingeben (getrennt durch ";" )""", "Zürich HB, Schweiz; Bern, Schweiz; Basel, Schweiz")
    # Erstellen einer Liste mit den separierten Abfahrtsorten
    start_locations_list = [x.strip() for x in start_locations.split(';')]

    # Abfrage des Ankuftsziels, mit default Wert Genf
    end_location = st.text_input("Zielort eingeben", "Genève, Schweiz")

    # Abfrage der Ankunftszeit aller Routen, kann aufgrund der convert_to_unix_timestamp funktion in normaler Schreibweise eingegeben werden
    arrival_time_str = st.text_input("Ankunftszeit eingeben", "13.05.2024-19:00", max_chars=16)

    # Diese Funktion wird nun angewendet
    arrival_time = convert_to_unix_timestamp(arrival_time_str)

    # Wenn alles richtig angegeben wurde kann nun normal weitergemacht werden
    # Alle in den vorherigen Funktionen gesammelten Daten werden nun zusammengebracht
    if api_key and start_locations_list and end_location and arrival_time is not None:
        for start_location in start_locations_list:
            start_lat, start_lng = get_coordinates(start_location, api_key)
            end_lat, end_lng = get_coordinates(end_location, api_key)
            # Abrufen der Zugroute und der Koordinaten
            train_route, route_coordinates = get_train_route(api_key, f"{start_lat},{start_lng}", f"{end_lat},{end_lng}", arrival_time)
            
            if train_route is not None:
                # Entferne die Spalte "Linie"
                train_route.drop(columns=['Linie'], inplace=True, errors='ignore')

                # Zeige die Zugroute als Tabelle an
                st.subheader(f"Zugroute von {start_location} nach {end_location}")
                st.write(train_route)

                # Erstellen der google maps Karten für die einzelnen Routen
                # Mit Hilfe von ChatGPT
                st.subheader(f"Zugroute von {start_location} nach {end_location} auf Karte anzeigen")
                st.markdown(f'<iframe width="100%" height="500" src="https://www.google.com/maps/embed/v1/directions?key={api_key}&origin={start_lat},{start_lng}&destination={end_lat},{end_lng}&mode=transit" allowfullscreen></iframe>', unsafe_allow_html=True)
            else:
                st.warning("Keine Route gefunden.")
    # Falls etwas falsch eingegeben wurde erscheint der folgende Error            
    else:
        st.warning("Bitte stellen Sie sicher, dass die Start- und Zielorte gültig sind, und verwenden Sie das richtige Datumsformat.")

# Ausführen der Hauptfunktion und damit starten der App
Endroute()