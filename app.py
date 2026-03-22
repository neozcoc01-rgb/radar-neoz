import streamlit as st
import requests
import folium
from folium import LayerControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Radar Urbex Pro", page_icon="🗺️")
st.title("🗺️ Radar Urbex Pro")
st.markdown("Scannez n'importe quelle ville pour trouver des lieux abandonnés via 7 bases de données mondiales.")

# --- LES 7 FONCTIONS DE RECHERCHE ---
# (On garde exactement votre moteur de recherche)

def chercher_osm_industrie(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(nwr["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["landuse"="brownfield"](around:{rayon_m},{lat},{lon});nwr["disused"="yes"](around:{rayon_m},{lat},{lon});nwr["historic"="factory"](around:{rayon_m},{lat},{lon});nwr["building"="industrial"]["abandoned"="yes"](around:{rayon_m},{lat},{lon}););out center;"""
    try: return requests.get(url, params={'data': query}).json().get('elements', [])
    except: return []

def chercher_osm_residentiel(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(nwr["abandoned:building"="residential"](around:{rayon_m},{lat},{lon});nwr["abandoned:building"="house"](around:{rayon_m},{lat},{lon});nwr["abandoned:building"="villa"](around:{rayon_m},{lat},{lon});nwr["building"="residential"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["building"="house"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["historic"="manor"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["historic"="castle"]["abandoned"="yes"](around:{rayon_m},{lat},{lon});nwr["building"="farm"]["abandoned"="yes"](around:{rayon_m},{lat},{lon}););out center;"""
    try: return requests.get(url, params={'data': query}).json().get('elements', [])
    except: return []

def chercher_osm_militaire_train(lat, lon, rayon_m):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];(nwr["military"="bunker"](around:{rayon_m},{lat},{lon});nwr["historic"="fort"](around:{rayon_m},{lat},{lon});nwr["railway"="abandoned"](around:{rayon_m},{lat},{lon});nwr["building"="train_station"]["disused"="yes"](around:{rayon_m},{lat},{lon}););out center;"""
    try: return requests.get(url, params={'data': query}).json().get('elements', [])
    except: return []

def chercher_base_merimee(lat, lon, rayon_m):
    url = "https://data.culture.gouv.fr/api/records/1.0/search/"
    params = {"dataset": "merimee-immeubles-proteges-au-titre-des-monuments-historiques", "q": "ruine OR vestige OR désaffecté OR ancienne usine OR friche", "geofilter.distance": f"{lat},{lon},{rayon_m}", "rows": 100}
    try: return [r for r in requests.get(url, params=params).json().get('records', []) if 'geometry' in r]
    except: return []

def chercher_wikidata(lat, lon, rayon_km):
    url = "https://query.wikidata.org/sparql"
    query = f"""SELECT ?place ?placeLabel ?location WHERE {{ SERVICE wikibase:around {{ ?place wdt:P625 ?location . bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral . bd:serviceParam wikibase:radius "{rayon_km}" . }} ?place wdt:P31/wdt:P279* ?type . VALUES ?type {{ wd:Q860861 wd:Q1303167 wd:Q273151 wd:Q109607 wd:Q144706 }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }} }}"""
    try: return requests.get(url, params={'format': 'json', 'query': query}, headers={'User-Agent': 'UrbexBot/4.0'}).json()['results']['bindings']
    except: return []

def chercher_wikipedia(lat, lon, rayon_m):
    url = "https://fr.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 500, "format": "json"}
    mots_cles = ["ruine", "abandonné", "désaffecté", "friche", "usine", "filature", "peignage", "fort", "bunker", "ancien"]
    try: return [a for a in requests.get(url, params=params).json().get('query', {}).get('geosearch', []) if any(m in a['title'].lower() for m in mots_cles)]
    except: return []

def chercher_wikimedia_commons(lat, lon, rayon_m):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}", "gsradius": min(rayon_m, 10000), "gslimit": 100, "format": "json"}
    mots_cles = ["abandoned", "ruin", "friche", "decay", "derelict", "bunker", "disused"]
    try: return [img for img in requests.get(url, params=params).json().get('query', {}).get('geosearch', []) if any(m in img['title'].lower() for m in mots_cles)]
    except: return []


# --- INTERFACE UTILISATEUR (Boutons et champs de texte) ---
col1, col2 = st.columns(2)
with col1:
    ville = st.text_input("Ville à scanner :", "Roubaix")
with col2:
    rayon_km = st.slider("Rayon (en km)", min_value=1, max_value=30, value=10)

# --- LE MOTEUR DE L'APPLICATION ---
if st.button("🚀 Lancer le Scan", use_container_width=True):
    
    # 1. On traduit la ville en GPS
    geolocator = Nominatim(user_agent="urbex_app_fr")
    location = geolocator.geocode(ville)
    
    if not location:
        st.error(f"Impossible de trouver la ville : {ville}. Vérifiez l'orthographe.")
    else:
        lat_centre = location.latitude
        lon_centre = location.longitude
        rayon_m = rayon_km * 1000
        
        st.success(f"📍 {ville} localisée ({lat_centre:.4f}, {lon_centre:.4f}). Scan en cours...")
        
        # 2. On lance les recherches avec une barre de chargement
        with st.spinner('Fouille des 7 bases de données (cela peut prendre 30 secondes)...'):
            l_osm_indus = chercher_osm_industrie(lat_centre, lon_centre, rayon_m)
            l_osm_resi = chercher_osm_residentiel(lat_centre, lon_centre, rayon_m)
            l_osm_mili = chercher_osm_militaire_train(lat_centre, lon_centre, rayon_m)
            l_merimee = chercher_base_merimee(lat_centre, lon_centre, rayon_m)
            l_wiki_data = chercher_wikidata(lat_centre, lon_centre, rayon_km)
            l_wikipedia = chercher_wikipedia(lat_centre, lon_centre, rayon_m)
            l_photos = chercher_wikimedia_commons(lat_centre, lon_centre, rayon_m)
            
            total_trouvailles = len(l_osm_indus) + len(l_osm_resi) + len(l_osm_mili) + len(l_merimee) + len(l_wiki_data) + len(l_wikipedia) + len(l_photos)
            
        st.info(f"✅ Terminé ! {total_trouvailles} lieux potentiels trouvés.")

        # 3. On crée la carte
        carte = folium.Map(location=[lat_centre, lon_centre], zoom_start=12)

        g_indus = folium.FeatureGroup(name='Industrie & Friches (Rouge)')
        g_resi = folium.FeatureGroup(name='Maisons & Manoirs (Rose)')
        g_mili = folium.FeatureGroup(name='Bunkers & Trains (Vert foncé)')
        g_gouv = folium.FeatureGroup(name='État Français - Mérimée (Orange)')
        g_wikidata = folium.FeatureGroup(name='Wikidata (Violet)')
        g_wikipedia = folium.FeatureGroup(name='Wikipédia (Noir)')
        g_photos = folium.FeatureGroup(name='Photos Commons (Bleu)')

        def ajouter_points(liste, groupe, couleur, icone='info-sign'):
            for l in liste:
                if 'geometry' in l: lat, lon, nom = l['geometry']['coordinates'][1], l['geometry']['coordinates'][0], l['fields'].get('tico', 'Lieu')
                elif 'location' in l: 
                    lon_str, lat_str = l['location']['value'].replace('Point(', '').replace(')', '').split()
                    lat, lon, nom = float(lat_str), float(lon_str), l['placeLabel']['value']
                elif 'lat' in l: lat, lon, nom = l['lat'], l['lon'], l.get('title', l.get('tags', {}).get('name', 'Lieu'))
                elif 'center' in l: lat, lon, nom = l['center']['lat'], l['center']['lon'], l.get('tags', {}).get('name', 'Bâtiment')
                else: continue
                
                popup_html = f"<b>{nom}</b><br><a href='https://www.google.com/maps/search/?api=1&query={lat},{lon}' target='_blank'>🗺️ Voir sur Google Maps</a>"
                folium.Marker([lat, lon], popup=popup_html, icon=folium.Icon(color=couleur, icon=icone)).add_to(groupe)

        ajouter_points(l_osm_indus, g_indus, 'red')
        ajouter_points(l_osm_resi, g_resi, 'pink', 'home')
        ajouter_points(l_osm_mili, g_mili, 'darkgreen', 'flag')
        ajouter_points(l_merimee, g_gouv, 'orange', 'institution')
        ajouter_points(l_wiki_data, g_wikidata, 'purple')
        ajouter_points(l_wikipedia, g_wikipedia, 'black')
        ajouter_points(l_photos, g_photos, 'blue', 'camera')

        for g in [g_indus, g_resi, g_mili, g_gouv, g_wikidata, g_wikipedia, g_photos]:
            g.add_to(carte)
        LayerControl().add_to(carte)

        # 4. On affiche la carte dans l'application
        st_folium(carte, width=700, height=500)
