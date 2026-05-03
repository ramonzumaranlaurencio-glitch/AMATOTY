import requests

def search_google_image(query, api_key, cse_id, num=1):
    """
    Busca imágenes en Google Custom Search y retorna la primera URL encontrada.
    """
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": cse_id,
        "key": api_key,
        "searchType": "image",
        "num": num,
        "safe": "active"
    }
    resp = requests.get(search_url, params=params)
    data = resp.json()
    if "items" in data:
        return [item["link"] for item in data["items"]]
    return []

# Ejemplo de uso:
# api_key = "TU_API_KEY"
# cse_id = "TU_CSE_ID"
# print(search_google_image("licuadora portatil", api_key, cse_id))
