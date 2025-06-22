import requests
from config import QURAN_API

def get_surah_list():
    res = requests.get(f"{QURAN_API}/surah")
    return res.json()["data"]

def get_surah(surah_number, edition="ar.alafasy"):
    res = requests.get(f"{QURAN_API}/surah/{surah_number}/{edition}")
    return res.json()["data"]

def get_ayah(surah_number, ayah_number, edition="ar.alafasy"):
    res = requests.get(f"{QURAN_API}/ayah/{surah_number}:{ayah_number}/{edition}")
    return res.json()["data"]

def search_ayah(query):
    res = requests.get(f"{QURAN_API}/search/{query}/all/ar")
    return res.json()["data"]["matches"]
