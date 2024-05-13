import streamlit as st
import googlemaps
import pandas as pd
import requests
from datetime import datetime

# Funktion zum Abrufen der Zugroute von Google Maps API mit einem GET-Request und festgelegter Ankunftszeit
def get_train_route(api_key, start_location, end_location, arrival_time):
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start_location}&destination={end_location}&mode=transit&transit_mode=rail&arrival_time={arrival_time}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Verarbeite die Daten und extrahiere relevante Informationen
        if "routes" in data and len(data["routes"]) > 0:
            steps = data["routes"][0]["legs"][0]["steps"]
            processed_data = []
            route_coordinates = []
            for step in steps:
                if step['travel_mode'] == 'TRANSIT':
                    departure_station = step['transit_details']['departure_stop']['name']
                    arrival_station = step['transit_details']['arrival_stop']['name']
                    # Linie entfernen
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

            return pd.DataFrame(processed_data), route_coordinates
    return None, None

# Funktion zur Umwandlung von Ortsnamen in Koordinaten
def get_coordinates(place, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
    return None, None

# Funktion zur Umwandlung von Datum und Uhrzeit in UNIX-Zeitstempel
def convert_to_unix_timestamp(datetime_str):
    try:
        datetime_obj = datetime.strptime(datetime_str, '%d.%m.%Y-%H:%M')
        unix_timestamp = int(datetime_obj.timestamp())-7200
        return unix_timestamp
    except ValueError:
        return None

# Hauptfunktion für die Streamlit-App
def main():
    # Setze den Titel der Streamlit-App
    st.title("TrainMeet")

    # Lese den API-Schlüssel aus Streamlit
    api_key = st.secrets["auth_key"]

    # Startorte eingeben
    start_locations = st.text_input("""Abfahrtsorte eingeben (getrennt durch ";" )""", "Zürich HB, Schweiz; Bern, Schweiz; Basel, Schweiz")
    start_locations_list = [x.strip() for x in start_locations.split(';')]

    # Zielort eingeben
    end_location = st.text_input("Zielort eingeben", "Genève, Schweiz")

    # Ankunftszeit für die Zugroute eingeben
    arrival_time_str = st.text_input("Ankunftszeit eingeben", "13.05.2024-19:00", max_chars=16)

    # Umwandlung des eingegebenen Datums in einen UNIX-Zeitstempel
    arrival_time = convert_to_unix_timestamp(arrival_time_str)

    # Wenn ein API-Schlüssel vorhanden ist und Start- und Zielort gültig sind
    if api_key and start_locations_list and end_location and arrival_time is not None:
        for start_location in start_locations_list:
            start_lat, start_lng = get_coordinates(start_location, api_key)
            end_lat, end_lng = get_coordinates(end_location, api_key)
            # Rufe die Zugroute und die Koordinaten ab
            train_route, route_coordinates = get_train_route(api_key, f"{start_lat},{start_lng}", f"{end_lat},{end_lng}", arrival_time)
            
            if train_route is not None:
                # Entferne die Spalte "Linie"
                train_route.drop(columns=['Linie'], inplace=True, errors='ignore')

                # Zeige die Zugroute als Tabelle an
                st.subheader(f"Zugroute von {start_location} nach {end_location}")
                st.write(train_route)

                # Erstelle eine Google Maps-Karte für die Zugroute
                st.subheader(f"Zugroute von {start_location} nach {end_location} auf Karte anzeigen")
                st.markdown(f'<iframe width="100%" height="500" src="https://www.google.com/maps/embed/v1/directions?key={api_key}&origin={start_lat},{start_lng}&destination={end_lat},{end_lng}&mode=transit" allowfullscreen></iframe>', unsafe_allow_html=True)
            else:
                st.warning("Keine Route gefunden.")
    else:
        st.warning("Bitte stellen Sie sicher, dass die Start- und Zielorte gültig sind, und verwenden Sie das richtige Datumsformat.")

# Starte die Streamlit-App
if __name__ == "__main__":
    main()