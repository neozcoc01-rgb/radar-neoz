import streamlit as st
import requests
import folium
import time
from folium import LayerControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Radar Urbex Pro", page_icon="🗺️")
st.title("🗺️ Radar Urbex Pro")
st.markdown("Scannez n'importe quelle ville pour trouver des lieux abandonnés avec une précision maximale.")

HEADERS_POLIS = {'User-Agent': 'RadarUrbexApp/3.0 (Smart Naming)'}

# --- LES 7 FONCTIONS (Filtres Équilibrés) ---
def chercher_osm_industrie(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(nwr["abandoned"="yes"]["building"="industrial"](around:{rayon_m},{lat},{lon});nwr["landuse"="brownfield"](around:{rayon_m},{lat},{lon});nwr["disused"="yes"]["building"="industrial"](around:{rayon_m},{lat},{lon});nwr["historic"="factory"](around:{rayon_m},{lat},{lon}););out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS).json().get('elements', [])
    except: return []

def chercher_osm_residentiel(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(nwr["abandoned:building"="residential"](around:{rayon_m},{lat},{lon});nwr["abandoned:building"="house"](around:{rayon_m},{lat},{lon});nwr["building"="residential"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["building"="house"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["building"="villa"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["historic"="manor"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["building"="farm"]["abandoned"="yes"](around:{rayon_m},{lat},{lon}););out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS).json().get('elements', [])
    except: return []

def chercher_osm_militaire_train(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    # Les bunkers et forts sont restaurés !
    query = f"""[out:json];(nwr["military"="bunker"](around:{rayon_m},{lat},{lon});nwr["historic"="fort"](around:{rayon_m},{lat},{lon});nwr["railway"="abandoned"](around:{rayon_m},{lat},{lon});nwr["building"="train_station"]["disused"="yes"](around:{rayon_m},{lat},{lon});nwr["building"="train_station"]["abandoned"="yes"](around:{rayon_m},{lat},{lon}););out center;"""
    try: return requests.get(url, params={'data': query}, headers=HEADERS_POLIS).json().get('elements', [])
    except: return []

def chercher_base_merimee(lat, lon, rayon_m):
    url = "https://data.culture.gouv.fr/api/records/1.0/search/"
    params = {"dataset": "merimee-immeubles-proteges-au-titre-des-monuments-historiques", "q": "ruine OR désaffecté OR friche OR vestige", "geofilter.distance": f"{lat},{lon},{rayon_m}", "rows": 100}
    try: return [r for r in requests.get(url, params=params, headers=HEADERS_POLIS).json().get('records', []) if 'geometry' in r]
    except: return []

def chercher_wikidata(lat, lon, rayon_km):
    url = "https://query.wikidata.org/sparql"
    # Q273151=Bâtiment abandonné, Q109607=Ruines, Q17028135=Ville fantôme
    query = f"""SELECT ?place ?placeLabel ?location WHERE {{ SERVICE wikibase:around {{ ?place wdt:P625 ?location . bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral . bd:serviceParam wikibase:radius "{rayon_km}" . }} ?place wdt:P31/wdt:P279* ?type . VALUES ?type {{ wd:Q273151 wd:Q109607 wd:Q17028135 }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }} }}"""
    try: return requests.get(url, params={'format': 'json', 'query': query}, headers=HEADERS_POLIS).json()['results']['bindings']
    except: return []

def chercher_wikipedia(lat, lon, rayon_m):
    url = "https://fr.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 500, "format": "json"}
    # Bunkers et forts restaurés ici aussi
    mots_cles = ["ruine", "abandonné", "désaffecté", "friche", "vestige", "fantôme", "détruit", "bunker", "fort"]
    try: return [a for a in requests.get(url, params=params, headers=HEADERS_POLIS).json().get('query', {}).get('geosearch', []) if any(m in a['title'].lower() for m in mots_cles)]
    except: return []

def chercher_wikimedia_commons(lat, lon, rayon_m):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 100, "format": "json"}
    mots_cles = ["abandoned", "ruin", "friche", "decay", "derelict", "disused", "urbex", "bunker"]
    try: return [img for img in requests.get(url, params=params, headers=HEADERS_POLIS).json().get('query', {}).get('geosearch', []) if any(m in img['title'].lower() for m in mots_cles)]
    except: return []


# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    ville = st.text_input("Ville à scanner :", "Roubaix")
with col2:
    rayon_km = st.slider("Rayon (en km)", min_value=1, max_value=30, value=10)

# --- MOTEUR ---
if st.button("🚀 Lancer le Scan Complet", use_container_width=True):
    
    geolocator = Nominatim(user_agent="radar_urbex_pro_v3")
    location = geolocator.geocode(ville)
    
    if not location:
        st.error(f"Impossible de trouver la ville : {ville}.")
    else:
        lat_centre = location.latitude
        lon_centre = location.longitude
        rayon_m = rayon_km * 1000
        
        st.success(f"📍 {ville} localisée. Scan anti-blocage en cours...")
        
        with st.spinner('Fouille des bases de données...'):
            l_osm_indus = chercher_osm_industrie(lat_centre, lon_centre, rayon_m)
            time.sleep(1.5)
            l_osm_resi = chercher_osm_residentiel(lat_centre, lon_centre, rayon_m)
            time.sleep(1.5)
            l_osm_mili = chercher_osm_militaire_train(lat_centre, lon_centre, rayon_m)
            time.sleep(1.5)
            l_merimee = chercher_base_merimee(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_wiki_data = chercher_wikidata(lat_centre, lon_centre, rayon_km)
            time.sleep(1)
            l_wikipedia = chercher_wikipedia(lat_centre, lon_centre, rayon_m)
            time.sleep(1)
            l_photos = chercher_wikimedia_commons(lat_centre, lon_centre, rayon_m)
            
            total = len(l_osm_indus) + len(l_osm_resi) + len(l_osm_mili) + len(l_merimee) + len(l_wiki_data) + len(l_wikipedia) + len(l_photos)
            
        st.info(f"✅ {total} lieux trouvés.")

        # --- CARTE ---
        carte = folium.Map(location=[lat_centre, lon_centre], zoom_start=12)

        g_indus = folium.FeatureGroup(name='Industrie & Friches (Rouge)')
        g_resi = folium.FeatureGroup(name='Maisons & Manoirs (Rose)')
        g_mili = folium.FeatureGroup(name='Bunkers & Trains (Vert foncé)')
        g_gouv = folium.FeatureGroup(name='État Français - Mérimée (Orange)')
        g_wikidata = folium.FeatureGroup(name='Wikidata (Violet)')
        g_wikipedia = folium.FeatureGroup(name='Wikipédia (Noir)')
        g_photos = folium.FeatureGroup(name='Photos Commons (Bleu)')

        # Le nouveau Cerveau pour nommer les lieux précisément
        def ajouter_points(liste, groupe, couleur, source_nom, icone='info-sign'):
            for l in liste:
                lat, lon, nom = None, None, "Lieu inconnu"
                
                # 1. Mérimée
                if 'geometry' in l and 'fields' in l:
                    lat, lon = l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]
                    nom = l['fields'].get('tico', 'Monument Historique')
                
                # 2. Wikidata
                elif 'location' in l and 'placeLabel' in l:
                    lon_str, lat_str = l['location']['value'].replace('Point(', '').replace(')', '').split()
                    lat, lon = float(lat_str), float(lon_str)
                    nom = l['placeLabel']['value']
                
                # 3. Wiki / Commons
                elif 'lat' in l and 'title' in l:
                    lat, lon = l['lat'], l['lon']
                    nom = l['title'].replace('File:', '')
                
                # 4. OpenStreetMap (Analyse intelligente des tags)
                elif 'tags' in l:
                    lat = l.get('lat') if 'lat' in l else l.get('center', {}).get('lat')
                    lon = l.get('lon') if 'lon' in l else l.get('center', {}).get('lon')
                    tags = l['tags']
                    
                    if 'name' in tags:
                        nom = tags['name'] # S'il a un vrai nom, on le garde
                    else:
                        # Sinon on devine ce que c'est !
                        if tags.get('military') == 'bunker': nom = 'Bunker'
                        elif tags.get('historic') == 'fort': nom = 'Fort historique'
                        elif tags.get('historic') == 'factory': nom = 'Ancienne usine / Filature'
                        elif tags.get('landuse') == 'brownfield': nom = 'Friche industrielle'
                        elif tags.get('railway') == 'abandoned': nom = 'Voie ferrée abandonnée'
                        elif tags.get('building') == 'train_station': nom = 'Ancienne gare'
                        elif 'abandoned:building' in tags: 
                            typ = tags['abandoned:building']
                            if typ in ['house', 'residential', 'detached']: nom = 'Maison abandonnée'
                            elif typ == 'villa': nom = 'Villa abandonnée'
                            elif typ == 'farm': nom = 'Ferme abandonnée'
                            else: nom = 'Bâtiment abandonné'
                        elif tags.get('building') == 'industrial': nom = 'Hangar / Bâtiment industriel'
                        elif tags.get('historic') == 'manor': nom = 'Manoir abandonné'
                        elif tags.get('historic') == 'castle': nom = 'Château en ruine'
                        else: nom = 'Lieu désaffecté'

                # Ajout sur la carte si on a trouvé des coordonnées
                if lat and lon:
                    popup_html = f"<b>{nom}</b><br><i>Source: {source_nom}</i><br><br><a href='https://www.google.com/maps/search/?api=1&query={lat},{lon}' target='_blank'>🗺️ Voir sur Google Maps</a>"
                    folium.Marker([lat, lon], popup=popup_html, icon=folium.Icon(color=couleur, icon=icone)).add_to(groupe)

        # On envoie les listes au cerveau
        ajouter_points(l_osm_indus, g_indus, 'red', 'OSM Industrie')
        ajouter_points(l_osm_resi, g_resi, 'pink', 'OSM Résidentiel', 'home')
        ajouter_points(l_osm_mili, g_mili, 'darkgreen', 'OSM Militaire', 'flag')
        ajouter_points(l_merimee, g_gouv, 'orange', 'Archives Mérimée', 'institution')
        ajouter_points(l_wiki_data, g_wikidata, 'purple', 'Wikidata')
        ajouter_points(l_wikipedia, g_wikipedia, 'black', 'Wikipédia')
        ajouter_points(l_photos, g_photos, 'blue', 'Wikimedia Commons', 'camera')

        for g in [g_indus, g_resi, g_mili, g_gouv, g_wikidata, g_wikipedia, g_photos]:
            g.add_to(carte)
        LayerControl().add_to(carte)

        st_folium(carte, width=700, height=500, returned_objects=[])
