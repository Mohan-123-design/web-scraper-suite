import getpass
import requests
import pandas as pd
import time
import re

API_ENDPOINT = "https://api.perplexity.ai/chat/completions"  # Corrected endpoint

def query_perplexity_sonar(prompt, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "top_p": 1,
        "max_tokens": 1000
    }
    response = requests.post(API_ENDPOINT, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def extract_webmd_url_from_response(response_json):
    # Try to extract doctor profile URL from multiple places
    try:
        # 1. web_results key in message (preferred)
        web_results = response_json['choices'][0]['message'].get('web_results', [])
        for item in web_results:
            url = item.get('url', '')
            if url.startswith("https://doctor.webmd.com/doctor/") and url.endswith("-overview"):
                return url
    except Exception:
        pass

    try:
        # 2. fallback: URLs in citations field
        citations = response_json.get('citations', [])
        for url in citations:
            if url.startswith("https://doctor.webmd.com/doctor/") and url.endswith("-overview"):
                return url
    except Exception:
        pass

    try:
        # 3. fallback: extract URL(s) from assistant's text content using regex
        content = response_json['choices'][0]['message'].get('content', '')
        urls_in_text = re.findall(r'https://doctor.webmd.com/doctor/[^\s]+-overview', content)
        if urls_in_text:
            return urls_in_text[0]
    except Exception:
        pass

    return ""

def main():
    api_key = getpass.getpass("Enter your Perplexity API key: ")

    input_csv = "Raw Data File.csv"
    output_csv = "doctors_with_webmd_urls.csv"

    df = pd.read_csv(input_csv)

    # Normalize column names for safe access
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        'npi id': 'npi_id',
        'first name': 'first_name',
        'last name': 'last_name',
        'gender': 'gender',
        'state': 'state',
        'specialisation': 'specialty',
        'bio': 'bio'
    })

    profile_urls = []
    for _, row in df.iterrows():
        prompt = (
            "Find doctor.webmd profile with the following input data:\n"
            f"Name: Dr. {row['first_name']} {row['last_name']}\n"
            f"Specialty: {row['specialty']}\n"
            f"Gender: {row['gender']}\n"
            f"Bio: {row['bio']}\n"
            f"Location: {row['state']}"
        )
        print(f"Querying Perplexity for Dr. {row['first_name']} {row['last_name']} ...")
        try:
            response = query_perplexity_sonar(prompt, api_key)
            url = extract_webmd_url_from_response(response)
        except Exception as e:
            print(f"API error for Dr. {row['first_name']} {row['last_name']}: {e}")
            url = ""
        profile_urls.append(url)
        time.sleep(1)  # polite delay to avoid rate limits

    df['webmd_profile_url'] = profile_urls
    df.to_csv(output_csv, index=False)
    print(f"Done! Results saved to '{output_csv}'")

if __name__ == "__main__":
    main()
