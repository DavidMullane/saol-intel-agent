import os
import json
import requests
import streamlit as st
import streamlit.components.v1 as components
import markdown
from google import genai
from google.genai import types

st.set_page_config(page_title="Studio Saol | Connected Intel Engine", layout="wide")

# --- NOTION API CONFIGURATION ---
# These tokens will be safely stored in Streamlit's Advanced Secrets Manager
NOTION_TOKEN = st.secrets.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = st.secrets.get("NOTION_DATABASE_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def load_historical_memory_from_notion(competitor_name: str) -> str:
    """Queries the Notion Database for an existing competitor entry to pull past context."""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return "No Notion credentials found. Operating without historical baseline."
        
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Competitor Name",
            "title": {
                "equals": competitor_name
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                # Extract the historical markdown text stored in the 'Intelligence Brief' property
                properties = results[0].get("properties", {})
                brief_content = properties.get("Intelligence Brief", {}).get("rich_text", [])
                if brief_content:
                    return brief_content[0].get("text", {}).get("content", "")
        return "No historical baseline recorded in Notion yet."
    except Exception:
        return "Error connecting to Notion. Proceeding with fresh landscape search."

def save_historical_memory_to_notion(competitor_name: str, industry: str, data_text: str):
    """Upserts the latest compiled agent intelligence brief directly into the team Notion workspace."""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return

    # Check if page already exists to update it, otherwise create a new one
    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {"filter": {"property": "Competitor Name", "title": {"equals": competitor_name}}}
    
    try:
        query_res = requests.post(query_url, json=payload, headers=HEADERS)
        results = query_res.json().get("results", [])
        
        # Notion text property chunking limit safety (caps at 2000 chars per element)
        truncated_text = data_text[:2000]

        page_properties = {
            "Competitor Name": {"title": [{"text": {"content": competitor_name}}]},
            "Industry Vertical": {"select": {"name": industry}},
            "Intelligence Brief": {"rich_text": [{"text": {"content": truncated_text}}]}
        }

        if results:
            # Update existing page
            page_id = results[0]["id"]
            url = f"https://api.notion.com/v1/pages/{page_id}"
            res = requests.patch(url, json={"properties": page_properties}, headers=HEADERS)
            
            # DIAGNOSTIC CHECK: Catch an update failure from Notion
            if res.status_code != 200:
                st.error(f"Notion Update Error ({res.status_code}): {res.text}")
        else:
            # Create a completely new entry page in their DB
            url = "https://api.notion.com/v1/pages"
            new_page_payload = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": page_properties
            }
            res = requests.post(url, json=new_page_payload, headers=HEADERS)
            
            # DIAGNOSTIC CHECK: Catch a creation failure from Notion
            if res.status_code != 200:
                st.error(f"Notion Creation Error ({res.status_code}): {res.text}")
                
    except Exception as e:
        st.warning(f"Could not sync data to Notion: {e}")

# --- CORE INTEL ENGINE ---
def run_automated_dashboard(client_name: str, competitor_name: str, industry: str, focus_area: str):
    client = genai.Client()
    
    # 1. READ FROM THE PERMANENT NOTION LEDGER
    past_memory = load_historical_memory_from_notion(competitor_name)
    
    system_instruction = (
        f"You are an expert {industry} Competitive Intelligence Analyst working for a premier strategy firm. "
        f"Your task is to organize data into an ultra-premium executive brief tailored for our client, {client_name}.\n\n"
        "CRITICAL FORMATTING RULES:\n"
        "1. NEVER output continuous text paragraphs or text blocks containing inline asterisks for financial or operational data.\n"
        "2. All metrics, financial quarters, and multi-year data MUST be structured using standard Markdown tables with explicit headers.\n"
        "3. Product threats, features, innovations, and facility updates MUST be broken into clean, scannable, indented bullet points.\n\n"
        "Structure the final output exactly with these headings:\n"
        "## 📊 Competitor Snapshot\n"
        "## 🔬 Product & Pipeline Threats\n"
        "## 🏭 Manufacturing & Supply Chain Footprint\n"
        "## 🤝 Recent M&A & Strategic Partnerships\n"
        "## 🛰️ Source Grounding"
    )
    
    user_prompt = f"""
    CLIENT: {client_name}
    COMPETITOR TARGET: {competitor_name}
    MARKET FOCUS: {focus_area}
    HISTORICAL MEMORY (Synthesize and build upon this baseline):\n{past_memory}
    
    INSTRUCTIONS: Perform a fresh search for recent Q1 2026 data. Synthesize old and new facts into formal Markdown tables and lists based on the rules.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1
        )
    )
    
    # 2. WRITE BACK TO THE PERMANENT NOTION LEDGER
    save_historical_memory_to_notion(competitor_name, industry, response.text)
    return response.text

# --- FRONTEND UI ---
st.title("Saol Intelligence Platform")
st.caption("Studio Prototyping Sandbox | Multi-User Notion Connected Engine")

with st.sidebar:
    st.header("⚡ Engine Configuration")
    client_input = st.text_input("Active Client Workspace", value="Johnson & Johnson MedTech")
    industry_input = st.text_input("Industry Vertical / Lens", value="MedTech")
    st.divider()
    competitor_input = st.text_input("Target Competitor to Profile", value="Boston Scientific")
    focus_input = st.text_area("Deep-Dive Focus Segments", value="Interventional Cardiology, Electrophysiology (PFA), and Endoscopy")
    
    generate_btn = st.button("🚀 Run Intelligence Sweep", type="primary")

if generate_btn:
    with st.spinner(f"Querying Notion database & scanning live 2026 web layers for {competitor_input}..."):
        try:
            raw_markdown = run_automated_dashboard(client_input, competitor_input, industry_input, focus_input)
            html_body = markdown.markdown(raw_markdown, extensions=['tables'])
            
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    :root {{
                        --bg-main: #f4f6f9; --card-bg: #ffffff; --text-main: #1e293b;
                        --border: #e2e8f0; --table-hdr: #f8fafc; --primary-dark: #1d4ed8;
                    }}
                    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background-color: var(--bg-main); color: var(--text-main); margin: 0; padding: 20px; }}
                    header {{ border-bottom: 2px solid var(--border); padding-bottom: 15px; margin-bottom: 30px; }}
                    h2 {{ font-size: 1.4rem; color: #0f172a; margin-top: 25px; }}
                    h2 + p, h2 + table, h2 + ul {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(15,23,42,0.03); }}
                    table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; }}
                    th, td {{ padding: 12px 16px; border-bottom: 1px solid var(--border); text-align: left; }}
                    th {{ background-color: var(--table-hdr); font-size: 0.75rem; text-transform: uppercase; }}
                    th:first-child, td:first-child {{ width: 240px; font-weight: 600; background-color: #fafafa; }}
                    ul {{ padding-left: 20px; }}
                    li {{ margin-bottom: 10px; }}
                </style>
            </head>
            <body>
                <header>
                    <h1 style='margin:0; font-size:1.8rem;'>Saol Intelligence Engine</h1>
                    <p style='color: #64748b; margin:4px 0 0 0;'>Client Workspace: <strong>{client_input}</strong> | Target: <strong>{competitor_input} ({industry_input})</strong></p>
                </header>
                <main>{html_body}</main>
            </body>
            </html>
            """
            
            components.html(styled_html, height=1400, scrolling=True)
            st.success("Executive Briefing successfully synchronized with Notion database context!")
            
        except Exception as e:
            st.error(f"Execution Error: {e}")
