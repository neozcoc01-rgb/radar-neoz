import streamlit as st
import requests
import folium
import time
from folium import LayerControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Radar Urbex Pro", page_icon="🎯")
st.title("🎯 Radar Urbex Pro (Mode Sniper)")
st.markdown("Recherche exclusive de **bâtiments physiques debout**. Les terrains vagues sont exclus.")

HEADERS_POLIS = {'User-Agent': 'RadarUrbexApp/5.0 (Sniper Mode)'}

# --- 1. INDUSTRIE (Murs obligatoires) ---
def chercher_osm_industrie(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    # On exige la balise "building" ou "abandoned:building"
    query = f"""[out:json];(
      nwr["building"="industrial"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
      nwr["building"="industrial"]["disused"="yes"](around:{rayon_m},{lat},{lon});
      nwr["building"]["historic"="factory"](around:{rayon_m},{lat},{lon});
      nwr["abandoned:building"="industrial"](around:{rayon_m},{lat},{lon});
      nwr["abandoned:building"="factory"](around:{rayon_m},{lat},{lon});
    );out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS).json().get('elements', [])
    except: return []

# --- 2. RÉSIDENTIEL (Murs obligatoires) ---
def chercher_osm_residentiel(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(
      nwr["abandoned:building"="residential"](around:{rayon_m},{lat},{lon});
      nwr["abandoned:building"="house"](around:{rayon_m},{lat},{lon});
      nwr["abandoned:building"="villa"](around:{rayon_m},{lat},{lon});
      nwr["abandoned:building"="farm"](around:{rayon_m},{lat},{lon});
      nwr["building"="house"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
      nwr["building"="villa"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
      nwr["building"]["historic"="manor"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
    );out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS).json().get('elements', [])
    except: return []

# --- 3. MILITAIRE (Voies ferrées supprimées) ---
def chercher_osm_militaire_train(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(
      nwr["military"="bunker"](around:{rayon_m},{lat},{lon});
      nwr["building"="bunker"](around:{rayon_m},{lat},{lon});
      nwr["building"]["historic"="fort"](around:{rayon_m},{lat},{lon});
      nwr["building"="train_station"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});
    );out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS).json().get('elements', [])
    except: return []

# --- 4, 5, 6, 7. ARCHIVES ET PHOTOS ---
def chercher_base_merimee(lat, lon, rayon_m):
    url = "https://data.culture.gouv.fr/api/records/1.0/search/"
    params = {"dataset": "merimee-immeubles-proteges-au-titre-des-monuments-historiques", "q": "ruine OR désaffecté OR friche OR vestige", "geofilter.distance": f"{lat},{lon},{rayon_m}", "rows": 50}
    try: return [r for r in requests.get(url, params=params, headers=HEADERS_POLIS).json().get('records', []) if 'geometry' in r]
    except: return []

def chercher_wikidata(lat, lon, rayon_km):
    url = "https://query.wikidata.org/sparql"
    query = f"""SELECT ?place ?placeLabel ?location WHERE {{ SERVICE wikibase:around {{ ?place wdt:P625 ?location . bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral . bd:serviceParam wikibase:radius "{rayon_km}" . }} ?place wdt:P31/wdt:P279* ?type . VALUES ?type {{ wd:Q273151 wd:Q109607 }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }} }}"""
    try: return requests.get(url, params={'format': 'json', 'query': query}, headers=HEADERS_POLIS).json()['results']['bindings']
    except: return []

def chercher_wikipedia(lat, lon, rayon_m):
    url = "https://fr.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 100, "format": "json"}
    mots_cles = ["ruine", "abandonné", "désaffecté", "friche", "vestige", "bunker", "fort"]
    try: return [a for a in requests.get(url, params=params, headers=HEADERS_POLIS).json().get('query', {}).get('geosearch', []) if any(m in a['title'].lower() for m in mots_cles)]
    except: return []

def chercher_wikimedia_commons(lat, lon, rayon_m):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 50, "format": "json"}
    mots_cles = ["abandoned", "ruin", "friche", "decay", "derelict", "urbex", "bunker"]
    try: return [img for img in requests.get(url, params=params, headers=HEADERS_POLIS).json().get('query', {}).get('geosearch', []) if any(m in img['title'].lower() for m in mots_cles)]
    except: return []

# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    ville = st.text_input("Ville à scanner :", "Roubaix")
with col2:
    rayon_km = st.slider("Rayon (en km)", min_value=1, max_value=30, value=10)

# --- MOTEUR ---
if st.button("🚀 Lancer le Scan Sniper", use_container_width=True):
    geolocator = Nominatim(user_agent="radar_urbex_sniper")
    location = geolocator.geocode(ville)
    
    if not location:
        st.error(f"Impossible de trouver la ville : {ville}.")
    else:
        lat_centre = location.latitude
        lon_centre = location.longitude
        rayon_m = rayon_km * 1000
        
        st.success(f"📍 {ville} localisée. Traque des bâtiments en cours...")
        
        with st.spinner('Fouille des bases de données...'):
            l_osm_indus = chercher_osm_industrie(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_osm_resi = chercher_osm_residentiel(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_osm_mili = chercher_osm_militaire_train(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_merimee = chercher_base_merimee(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_wiki_data = chercher_wikidata(lat_centre, lon_centre, rayon_km)
            time.sleep(1)
            l_wikipedia = chercher_wikipedia(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_photos = chercher_wikimedia_commons(lat_centre, lon_centre, rayon_m)
            
            total = len(l_osm_indus) + len(l_osm_resi) + len(l_osm_mili) + len(l_merimee) + len(l_wiki_data) + len(l_wikipedia) + len(l_photos)
            
        st.info(f"✅ {total} structures trouvées.")

        # --- CARTE ---
        carte = folium.Map(location=[lat_centre, lon_centre], zoom_start=12)

        g_indus = folium.FeatureGroup(name='Industrie (Murs confirmés)')
        g_resi = folium.FeatureGroup(name='Maisons & Manoirs (Murs confirmés)')
        g_mili = folium.FeatureGroup(name='Bunkers & Gares')
        g_archives = folium.FeatureGroup(name='Archives (Attention: Peut être détruit)')
        g_photos = folium.FeatureGroup(name='Photos Commons (Bleu)')

        def ajouter_points(liste, groupe, couleur, source_nom, icone='info-sign', is_archive=False):
            for l in liste:
                lat, lon, nom = None, None, "Bâtiment inconnu"
                
                if 'fields' in l and 'tico' in l['fields']:
                    lat, lon, nom = l['geometry']['coordinates'][1], l['geometry']['coordinates'][0], l['fields']['tico']
                elif 'placeLabel' in l:
                    try:
                        lon_str, lat_str = l['location']['value'].replace('Point(', '').replace(')', '').split()
                        lat, lon, nom = float(lat_str), float(lon_str), l['placeLabel']['value']
                    except: continue
                elif 'title' in l and 'lat' in l and 'tags' not in l:
                    lat, lon, nom = l['lat'], l['lon'], l['title'].replace('File:', '')
                elif 'tags' in l:
                    lat = l.get('lat', l.get('center', {}).get('lat'))
                    lon = l.get('lon', l.get('center', {}).get('lon'))
                    tags = l.get('tags', {})
                    nom_officiel = tags.get('name')
                    type_devine = "Bâtiment abandonné"
                    
                    if tags.get('military') == 'bunker' or tags.get('building') == 'bunker': type_devine = "Bunker de guerre"
                    elif tags.get('building') == 'industrial': type_devine = "Bâtiment industriel / Usine"
                    elif tags.get('abandoned:building') in ['house', 'residential'] or tags.get('building') == 'house': type_devine = "Maison abandonnée"
                    elif tags.get('abandoned:building') == 'villa': type_devine = "Villa abandonnée"
                    elif tags.get('abandoned:building') == 'farm': type_devine = "Ferme abandonnée"
                    elif tags.get('building') == 'train_station': type_devine = "Gare abandonnée"
                    elif tags.get('historic') == 'manor': type_devine = "Manoir"

                    nom = f"{nom_officiel} ({type_devine})" if nom_officiel else type_devine

                if lat and lon:
                    avertissement = "<br><b style='color:red;'>⚠️ Source Historique (Peut avoir été rasé)</b>" if is_archive else ""
                    lien = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    popup_html = f"<b>{nom}</b><br><i>Source: {source_nom}</i>{avertissement}<br><br><a href='{lien}' target='_blank'>🗺️ Passer en Vue Satellite (Google Maps)</a>"
                    folium.Marker([lat, lon], popup=popup_html, icon=folium.Icon(color=couleur, icon=icone)).add_to(groupe)

        # Les sources OSM sont sûres (bâtiments debout)
        ajouter_points(l_osm_indus, g_indus, 'red', 'OSM Industrie')
        ajouter_points(l_osm_resi, g_resi, 'pink', 'OSM Résidentiel', 'home')
        ajouter_points(l_osm_mili, g_mili, 'darkgreen', 'OSM Militaire', 'flag')
        
        # Les sources Encyclopédiques sont mises dans un calque d'archives avec alerte
        ajouter_points(l_merimee, g_archives, 'orange', 'Archives Mérimée', 'book', is_archive=True)
        ajouter_points(l_wiki_data, g_archives, 'purple', 'Wikidata', 'book', is_archive=True)
        ajouter_points(l_wikipedia, g_archives, 'black', 'Wikipédia', 'book', is_archive=True)
        
        ajouter_points(l_photos, g_photos, 'blue', 'Wikimedia Commons', 'camera')

        for g in [g_indus, g_resi, g_mili, g_archives, g_photos]:
            g.add_to(carte)
        LayerControl().add_to(carte)

        st_folium(carte, width=700, height=500, returned_objects=[])
