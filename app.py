import streamlit as st
import requests
import folium
import time
from folium import LayerControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Radar Urbex Pro", page_icon="🏭")
st.title("🏭 Radar Urbex Pro")
st.markdown("Recherche massive de bâtiments abandonnés, désaffectés et friches industrielles.")

HEADERS_POLIS = {'User-Agent': 'RadarUrbexApp/7.0'}

# --- 1. OSM BÂTIMENTS (Abandonnés, Désaffectés, Ruines) ---
def chercher_osm_batiments(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(
      nwr["building"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
      nwr["building"]["disused"="yes"](around:{rayon_m},{lat},{lon});
      nwr["abandoned:building"](around:{rayon_m},{lat},{lon});
      nwr["disused:building"](around:{rayon_m},{lat},{lon});
      nwr["building"="ruins"](around:{rayon_m},{lat},{lon});
      nwr["historic"="ruins"](around:{rayon_m},{lat},{lon});
      nwr["ruins"="yes"](around:{rayon_m},{lat},{lon});
    );out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS, timeout=12).json().get('elements', [])
    except: return []

# --- 2. OSM FRICHES & USINES (Le Saint-Graal du Nord) ---
def chercher_osm_friches(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(
      nwr["landuse"="brownfield"](around:{rayon_m},{lat},{lon});
      nwr["historic"="factory"](around:{rayon_m},{lat},{lon});
      nwr["man_made"="works"]["disused"="yes"](around:{rayon_m},{lat},{lon});
      nwr["man_made"="works"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
    );out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS, timeout=12).json().get('elements', [])
    except: return []

# --- 3. OSM MILITAIRE (Bunkers & Forts) ---
def chercher_osm_militaire(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(
      nwr["military"="bunker"](around:{rayon_m},{lat},{lon});
      nwr["historic"="fort"](around:{rayon_m},{lat},{lon});
    );out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS, timeout=10).json().get('elements', [])
    except: return []

# --- 4. ARCHIVES MÉRIMÉE ---
def chercher_base_merimee(lat, lon, rayon_m):
    url = "https://data.culture.gouv.fr/api/records/1.0/search/"
    params = {"dataset": "merimee-immeubles-proteges-au-titre-des-monuments-historiques", "q": "ruine OR désaffecté OR friche OR vestige", "geofilter.distance": f"{lat},{lon},{rayon_m}", "rows": 50}
    try: return [r for r in requests.get(url, params=params, headers=HEADERS_POLIS, timeout=10).json().get('records', []) if 'geometry' in r]
    except: return []

# --- 5. WIKIDATA ---
def chercher_wikidata(lat, lon, rayon_km):
    url = "https://query.wikidata.org/sparql"
    query = f"""SELECT ?place ?placeLabel ?location WHERE {{ SERVICE wikibase:around {{ ?place wdt:P625 ?location . bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral . bd:serviceParam wikibase:radius "{rayon_km}" . }} ?place wdt:P31/wdt:P279* ?type . VALUES ?type {{ wd:Q273151 wd:Q109607 }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }} }}"""
    try: return requests.get(url, params={'format': 'json', 'query': query}, headers=HEADERS_POLIS, timeout=10).json()['results']['bindings']
    except: return []

# --- 6. WIKIPÉDIA ---
def chercher_wikipedia(lat, lon, rayon_m):
    url = "https://fr.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 100, "format": "json"}
    mots_cles = ["ruine", "abandonné", "désaffecté", "friche", "vestige", "bunker", "fort"]
    try: return [a for a in requests.get(url, params=params, headers=HEADERS_POLIS, timeout=10).json().get('query', {}).get('geosearch', []) if any(m in a['title'].lower() for m in mots_cles)]
    except: return []

# --- 7. COMMONS (Photos) ---
def chercher_wikimedia_commons(lat, lon, rayon_m):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 50, "format": "json"}
    mots_cles = ["abandoned", "ruin", "friche", "decay", "derelict", "urbex", "bunker"]
    try: return [img for img in requests.get(url, params=params, headers=HEADERS_POLIS, timeout=10).json().get('query', {}).get('geosearch', []) if any(m in img['title'].lower() for m in mots_cles)]
    except: return []


# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    ville = st.text_input("Ville à scanner :", "Roubaix")
with col2:
    rayon_km = st.slider("Rayon (en km)", min_value=1, max_value=30, value=15)

# --- MOTEUR ---
if st.button("🚀 Lancer le Scan Massif", use_container_width=True):
    geolocator = Nominatim(user_agent="radar_urbex_v7")
    location = geolocator.geocode(ville)
    
    if not location:
        st.error(f"Impossible de trouver la ville : {ville}.")
    else:
        lat_centre = location.latitude
        lon_centre = location.longitude
        rayon_m = rayon_km * 1000
        
        st.success(f"📍 {ville} localisée. Ratissage de la zone en cours...")
        
        with st.spinner('Récupération de toutes les données...'):
            l_osm_batiments = chercher_osm_batiments(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_osm_friches = chercher_osm_friches(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_osm_mili = chercher_osm_militaire(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_merimee = chercher_base_merimee(lat_centre, lon_centre, rayon_m)
            time.sleep(0.5)
            l_wiki_data = chercher_wikidata(lat_centre, lon_centre, rayon_km)
            time.sleep(0.5)
            l_wikipedia = chercher_wikipedia(lat_centre, lon_centre, rayon_m)
            time.sleep(0.5)
            l_photos = chercher_wikimedia_commons(lat_centre, lon_centre, rayon_m)
            
            total = len(l_osm_batiments) + len(l_osm_friches) + len(l_osm_mili) + len(l_merimee) + len(l_wiki_data) + len(l_wikipedia) + len(l_photos)
            
        st.info(f"✅ {total} lieux trouvés. L'exploration peut commencer !")

        # --- CARTE ---
        carte = folium.Map(location=[lat_centre, lon_centre], zoom_start=12)

        g_batiments = folium.FeatureGroup(name='Bâtiments (Abandonné/Désaffecté) - Rouge')
        g_friches = folium.FeatureGroup(name='Friches & Usines - Orange')
        g_mili = folium.FeatureGroup(name='Bunkers & Forts - Vert')
        g_archives = folium.FeatureGroup(name='Archives (Wikipédia/État) - Noir')
        g_photos = folium.FeatureGroup(name='Photos d\'Urbex - Bleu')

        def ajouter_points(liste, groupe, couleur, source_nom, icone='info-sign'):
            for l in liste:
                lat, lon, nom = None, None, "Lieu inconnu"
                
                # Format Mérimée
                if 'fields' in l and 'tico' in l['fields']:
                    lat, lon, nom = l['geometry']['coordinates'][1], l['geometry']['coordinates'][0], l['fields']['tico']
                # Format Wikidata
                elif 'placeLabel' in l:
                    try:
                        lon_str, lat_str = l['location']['value'].replace('Point(', '').replace(')', '').split()
                        lat, lon, nom = float(lat_str), float(lon_str), l['placeLabel']['value']
                    except: continue
                # Format Wikipedia/Commons
                elif 'title' in l and 'lat' in l and 'tags' not in l:
                    lat, lon, nom = l['lat'], l['lon'], l['title'].replace('File:', '')
                # Format OSM
                elif 'tags' in l:
                    lat = l.get('lat', l.get('center', {}).get('lat'))
                    lon = l.get('lon', l.get('center', {}).get('lon'))
                    tags = l.get('tags', {})
                    
                    nom_officiel = tags.get('name')
                    
                    if tags.get('landuse') == 'brownfield': type_devine = "Friche Industrielle"
                    elif tags.get('historic') == 'factory': type_devine = "Ancienne Usine"
                    elif tags.get('military') == 'bunker': type_devine = "Bunker"
                    elif tags.get('building') == 'ruins' or tags.get('ruins') == 'yes': type_devine = "Ruines"
                    elif tags.get('disused') == 'yes' or 'disused:building' in tags: type_devine = "Bâtiment Désaffecté"
                    elif tags.get('abandoned') == 'yes' or 'abandoned:building' in tags: type_devine = "Bâtiment Abandonné"
                    else: type_devine = "Lieu Désaffecté"

                    nom = f"{nom_officiel} ({type_devine})" if nom_officiel else type_devine

                if lat and lon:
                    lien = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    popup_html = f"<b>{nom}</b><br><i>Source: {source_nom}</i><br><br><a href='{lien}' target='_blank'>🗺️ Ouvrir Google Maps</a>"
                    folium.Marker([lat, lon], popup=popup_html, icon=folium.Icon(color=couleur, icon=icone)).add_to(groupe)

        ajouter_points(l_osm_batiments, g_batiments, 'red', 'OpenStreetMap', 'home')
        ajouter_points(l_osm_friches, g_friches, 'orange', 'OpenStreetMap', 'wrench')
        ajouter_points(l_osm_mili, g_mili, 'darkgreen', 'OpenStreetMap', 'flag')
        
        ajouter_points(l_merimee, g_archives, 'black', 'Base Mérimée', 'book')
        ajouter_points(l_wiki_data, g_archives, 'black', 'Wikidata', 'book')
        ajouter_points(l_wikipedia, g_archives, 'black', 'Wikipédia', 'book')
        
        ajouter_points(l_photos, g_photos, 'blue', 'Wikimedia Commons', 'camera')

        for g in [g_batiments, g_friches, g_mili, g_archives, g_photos]:
            g.add_to(carte)
        LayerControl().add_to(carte)

        st_folium(carte, width=700, height=500, returned_objects=[])
