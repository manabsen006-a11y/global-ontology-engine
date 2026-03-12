"""
app/ps_crm/osint/entity_data.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Entity Knowledge Base for Cross-Domain Intelligence Correlation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Contains structured entity dictionaries for countries, organizations,
people, resources, and event types. Used by the CorrelationEngine to
extract and match entities across domain signals.
"""

from typing import Dict, List, Set

# ─────────────────────────────────────────────────────────────────────────────
# Countries & Regions (name → set of aliases/keywords)
# ─────────────────────────────────────────────────────────────────────────────
COUNTRIES: Dict[str, Set[str]] = {
    "india": {"india", "bharat", "new delhi", "modi", "indian"},
    "china": {"china", "beijing", "prc", "chinese", "xi jinping"},
    "usa": {"usa", "united states", "america", "washington", "u.s.", "us ", "american", "white house", "pentagon", "biden", "trump"},
    "russia": {"russia", "moscow", "kremlin", "russian", "putin"},
    "iran": {"iran", "tehran", "iranian", "persian", "khamenei", "raisi"},
    "pakistan": {"pakistan", "islamabad", "pakistani"},
    "israel": {"israel", "tel aviv", "jerusalem", "israeli", "netanyahu", "idf"},
    "ukraine": {"ukraine", "kyiv", "ukrainian", "zelensky", "zelenskyy"},
    "taiwan": {"taiwan", "taipei", "taiwanese"},
    "north korea": {"north korea", "pyongyang", "dprk", "kim jong"},
    "south korea": {"south korea", "seoul", "korean"},
    "japan": {"japan", "tokyo", "japanese"},
    "germany": {"germany", "berlin", "german"},
    "france": {"france", "paris", "french", "macron"},
    "uk": {"uk", "united kingdom", "britain", "british", "london", "england"},
    "australia": {"australia", "canberra", "australian"},
    "canada": {"canada", "ottawa", "canadian", "trudeau"},
    "brazil": {"brazil", "brasilia", "brazilian", "lula"},
    "saudi arabia": {"saudi", "saudi arabia", "riyadh", "mbs", "mohammed bin salman"},
    "turkey": {"turkey", "türkiye", "ankara", "turkish", "erdogan"},
    "egypt": {"egypt", "cairo", "egyptian"},
    "iraq": {"iraq", "baghdad", "iraqi"},
    "syria": {"syria", "damascus", "syrian"},
    "afghanistan": {"afghanistan", "kabul", "afghan", "taliban"},
    "venezuela": {"venezuela", "caracas", "venezuelan", "maduro"},
    "myanmar": {"myanmar", "burma", "naypyidaw"},
    "ethiopia": {"ethiopia", "addis ababa", "ethiopian"},
    "nigeria": {"nigeria", "abuja", "nigerian"},
    "south africa": {"south africa", "pretoria", "south african"},
    "indonesia": {"indonesia", "jakarta", "indonesian"},
    "mexico": {"mexico", "mexico city", "mexican"},
    "uae": {"uae", "united arab emirates", "abu dhabi", "dubai", "emirati"},
    "qatar": {"qatar", "doha", "qatari"},
    "philippines": {"philippines", "manila", "philippine", "filipino"},
    "vietnam": {"vietnam", "hanoi", "vietnamese"},
    "thailand": {"thailand", "bangkok", "thai"},
    "singapore": {"singapore", "singaporean"},
    "malaysia": {"malaysia", "kuala lumpur", "malaysian"},
    "bangladesh": {"bangladesh", "dhaka", "bangladeshi"},
    "sri lanka": {"sri lanka", "colombo", "sri lankan"},
    "nepal": {"nepal", "kathmandu", "nepali"},
    "cuba": {"cuba", "havana", "cuban"},
    "colombia": {"colombia", "bogota", "colombian"},
    "argentina": {"argentina", "buenos aires", "argentinian"},
    "chile": {"chile", "santiago", "chilean"},
    "poland": {"poland", "warsaw", "polish"},
    "italy": {"italy", "rome", "italian"},
    "spain": {"spain", "madrid", "spanish"},
    "greece": {"greece", "athens", "greek"},
    "netherlands": {"netherlands", "amsterdam", "dutch"},
    "sweden": {"sweden", "stockholm", "swedish"},
    "finland": {"finland", "helsinki", "finnish"},
    "norway": {"norway", "oslo", "norwegian"},
    "denmark": {"denmark", "copenhagen", "danish"},
    "switzerland": {"switzerland", "zurich", "bern", "swiss"},
    "belgium": {"belgium", "brussels", "belgian"},
    "austria": {"austria", "vienna", "austrian"},
    "hungary": {"hungary", "budapest", "hungarian"},
    "czech republic": {"czech", "prague"},
    "romania": {"romania", "bucharest", "romanian"},
    "portugal": {"portugal", "lisbon", "portuguese"},
    "ireland": {"ireland", "dublin", "irish"},
    "new zealand": {"new zealand", "wellington", "kiwi"},
    "jordan": {"jordan", "amman", "jordanian"},
    "lebanon": {"lebanon", "beirut", "lebanese", "hezbollah"},
    "yemen": {"yemen", "sanaa", "yemeni", "houthi"},
    "libya": {"libya", "tripoli", "libyan"},
    "sudan": {"sudan", "khartoum", "sudanese"},
    "somalia": {"somalia", "mogadishu", "somali"},
    "kenya": {"kenya", "nairobi", "kenyan"},
    "morocco": {"morocco", "rabat", "moroccan"},
    "algeria": {"algeria", "algiers", "algerian"},
    "tunisia": {"tunisia", "tunis", "tunisian"},
    "kazakhstan": {"kazakhstan", "astana", "kazakh"},
    "uzbekistan": {"uzbekistan", "tashkent", "uzbek"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Organizations (name → set of aliases)
# ─────────────────────────────────────────────────────────────────────────────
ORGANIZATIONS: Dict[str, Set[str]] = {
    # Military alliances
    "NATO": {"nato", "north atlantic treaty", "atlantic alliance"},
    "QUAD": {"quad", "quadrilateral security dialogue"},
    "AUKUS": {"aukus"},
    "SCO": {"sco", "shanghai cooperation"},
    "CSTO": {"csto", "collective security treaty"},

    # Economic blocs
    "BRICS": {"brics", "brics+"},
    "EU": {"eu", "european union"},
    "ASEAN": {"asean", "association of southeast asian nations"},
    "G7": {"g7", "group of seven"},
    "G20": {"g20", "group of twenty"},
    "OPEC": {"opec", "opec+", "oil producing"},
    "APEC": {"apec"},
    "MERCOSUR": {"mercosur"},

    # International bodies
    "UN": {"un", "united nations", "unga", "unsc", "security council"},
    "WHO": {"who", "world health organization"},
    "WTO": {"wto", "world trade organization"},
    "IMF": {"imf", "international monetary fund"},
    "World Bank": {"world bank"},
    "IAEA": {"iaea", "international atomic energy"},
    "ICC": {"icc", "international criminal court"},
    "UNHCR": {"unhcr", "refugees"},
    "FATF": {"fatf", "financial action task force"},

    # Intelligence & defense agencies
    "CIA": {"cia", "central intelligence agency", "langley"},
    "FBI": {"fbi", "federal bureau"},
    "NSA": {"nsa", "national security agency"},
    "MI6": {"mi6", "secret intelligence service"},
    "Mossad": {"mossad"},
    "ISI": {"isi", "inter-services intelligence"},
    "RAW": {"raw", "research and analysis wing"},
    "FSB": {"fsb", "federal security service"},
    "DGSE": {"dgse"},
    "BND": {"bnd", "bundesnachrichtendienst"},

    # Defense entities
    "IDF": {"idf", "israel defense forces"},
    "PLA": {"pla", "people's liberation army"},
    "Wagner": {"wagner", "prigozhin"},

    # Tech companies
    "TSMC": {"tsmc", "taiwan semiconductor"},
    "ASML": {"asml"},
    "Nvidia": {"nvidia"},
    "OpenAI": {"openai", "gpt-5", "chatgpt"},
    "Google": {"google", "alphabet", "deepmind", "gemini"},
    "Microsoft": {"microsoft"},
    "Meta": {"meta", "facebook"},
    "Apple": {"apple"},
    "Amazon": {"amazon", "aws"},
    "Huawei": {"huawei"},
    "ISRO": {"isro", "indian space research"},
    "NASA": {"nasa"},
    "SpaceX": {"spacex", "starlink"},

    # Energy & resource
    "Aramco": {"aramco", "saudi aramco"},
    "Gazprom": {"gazprom"},
    "Rosneft": {"rosneft"},
    "Shell": {"shell", "royal dutch"},
    "BP": {"bp", "british petroleum"},
    "ExxonMobil": {"exxonmobil", "exxon"},
    "Chevron": {"chevron"},
    "TotalEnergies": {"totalenergies", "total energies"},

    # Financial
    "BlackRock": {"blackrock"},
    "Vanguard": {"vanguard"},
    "Goldman Sachs": {"goldman sachs"},
    "JPMorgan": {"jpmorgan", "jp morgan"},

    # Misc
    "Hamas": {"hamas"},
    "Hezbollah": {"hezbollah", "hizbollah"},
    "ISIS": {"isis", "isil", "islamic state", "daesh"},
    "Al-Qaeda": {"al-qaeda", "al qaeda"},
    "Red Cross": {"red cross", "icrc"},
    "Amnesty International": {"amnesty international", "amnesty"},
    "Greenpeace": {"greenpeace"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Key People (name → set of aliases)
# ─────────────────────────────────────────────────────────────────────────────
KEY_PEOPLE: Dict[str, Set[str]] = {
    "Narendra Modi": {"modi", "narendra modi", "pm modi"},
    "Xi Jinping": {"xi jinping", "xi", "president xi"},
    "Donald Trump": {"trump", "donald trump"},
    "Joe Biden": {"biden", "joe biden"},
    "Vladimir Putin": {"putin", "vladimir putin"},
    "Volodymyr Zelensky": {"zelensky", "zelenskyy", "volodymyr"},
    "Benjamin Netanyahu": {"netanyahu", "bibi"},
    "Kim Jong Un": {"kim jong un", "kim jong-un"},
    "Ayatollah Khamenei": {"khamenei", "ayatollah", "supreme leader"},
    "Mohammad bin Salman": {"mbs", "bin salman", "mohammad bin salman"},
    "Recep Erdogan": {"erdogan", "recep tayyip"},
    "Emmanuel Macron": {"macron", "emmanuel macron"},
    "Olaf Scholz": {"scholz", "olaf scholz"},
    "Rishi Sunak": {"sunak", "rishi sunak"},
    "Justin Trudeau": {"trudeau", "justin trudeau"},
    "Lula da Silva": {"lula", "lula da silva"},
    "Nicolas Maduro": {"maduro", "nicolas maduro"},
    "Bashar al-Assad": {"assad", "bashar"},
    "Ebrahim Raisi": {"raisi", "ebrahim raisi"},
    "Mark Rutte": {"rutte", "mark rutte"},
    "Jens Stoltenberg": {"stoltenberg"},
    "Antonio Guterres": {"guterres", "un secretary"},
    "Elon Musk": {"elon musk", "musk"},
    "Jeff Bezos": {"bezos", "jeff bezos"},
    "Mark Zuckerberg": {"zuckerberg"},
    "Jeffrey Epstein": {"epstein", "jeffrey epstein"},
    "S. Jaishankar": {"jaishankar", "s jaishankar"},
    "Rajnath Singh": {"rajnath", "rajnath singh"},
    "Amit Shah": {"amit shah"},
    "Yogi Adityanath": {"yogi", "adityanath"},
    "Arvind Kejriwal": {"kejriwal"},
    "Rahul Gandhi": {"rahul gandhi"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Strategic Resources
# ─────────────────────────────────────────────────────────────────────────────
RESOURCES: Dict[str, Set[str]] = {
    "oil": {"oil", "petroleum", "crude", "barrel", "brent", "wti", "petrol", "diesel", "fuel", "opec"},
    "natural gas": {"natural gas", "lng", "pipeline", "nord stream", "gas supply"},
    "uranium": {"uranium", "nuclear fuel", "enrichment", "centrifuge", "yellowcake"},
    "semiconductors": {"semiconductor", "chip", "fab", "foundry", "wafer", "tsmc", "asml", "nanometer"},
    "rare earth": {"rare earth", "lithium", "cobalt", "neodymium", "gallium", "germanium", "critical minerals"},
    "gold": {"gold", "bullion", "gold reserves"},
    "wheat": {"wheat", "grain", "cereal", "food supply", "food security"},
    "water": {"water supply", "freshwater", "water crisis", "desalination", "aquifer"},
    "arms": {"arms deal", "weapons", "munitions", "arms export", "defense contract", "military hardware"},
    "currency": {"dollar", "yuan", "renminbi", "rupee", "euro", "de-dollarization", "forex", "reserve currency"},
    "data": {"data", "surveillance", "data sovereignty", "cloud", "data center"},
    "space assets": {"satellite", "orbit", "space station", "gps", "space debris"},
    "AI compute": {"ai compute", "gpu", "ai chip", "training cluster", "compute power"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Event Types (used for signal classification)
# ─────────────────────────────────────────────────────────────────────────────
EVENT_TYPES: Dict[str, Set[str]] = {
    # Geopolitical
    "diplomatic_talks": {"summit", "bilateral", "talks", "diplomatic", "negotiation", "dialogue", "envoy"},
    "sanctions": {"sanction", "embargo", "trade ban", "blacklist", "restrict"},
    "treaty": {"treaty", "agreement", "pact", "accord", "memorandum"},
    "territorial_dispute": {"border", "territorial", "sovereignty", "annex", "occupy", "incursion"},

    # Military / Defense
    "military_exercise": {"military exercise", "naval exercise", "war games", "drills", "deployment"},
    "missile_test": {"missile test", "missile launch", "ballistic", "hypersonic", "icbm"},
    "nuclear_test": {"nuclear test", "underground test", "nuclear detonation", "critical mass"},
    "nuclear_program": {"nuclear program", "enrichment", "centrifuge", "nuclear weapon", "warhead", "nuclear power plant", "nuclear capable"},
    "arms_deal": {"arms deal", "defense deal", "weapons sale", "military aid", "arms transfer"},
    "cyber_attack": {"cyber attack", "hack", "ransomware", "apt", "cyber espionage", "data breach"},
    "military_conflict": {"war", "invasion", "airstrike", "bombardment", "offensive", "military operation"},

    # Economic
    "trade_deal": {"trade deal", "trade agreement", "free trade", "tariff", "trade war"},
    "investment": {"investment", "fdi", "funding", "capital", "venture", "stake"},
    "port_development": {"port", "chabahar", "hambantota", "gwadar", "port development", "maritime trade"},
    "oil_market": {"oil price", "oil supply", "oil production", "oil field", "refinery", "oil export"},
    "debt_crisis": {"debt", "default", "bailout", "imf loan", "fiscal crisis", "credit rating"},
    "currency_move": {"devaluation", "forex", "currency war", "de-dollarization", "digital currency"},

    # Climate / Natural
    "earthquake": {"earthquake", "seismic", "tremor", "richter", "magnitude", "quake"},
    "tectonic_activity": {"tectonic", "plate", "fault line", "seismograph", "geological"},
    "extreme_weather": {"hurricane", "typhoon", "cyclone", "flood", "drought", "wildfire", "heatwave"},
    "emissions": {"emission", "carbon", "greenhouse", "methane", "climate target"},

    # Social
    "protest": {"protest", "demonstration", "unrest", "riot", "uprising", "rally", "march"},
    "regime_change": {"regime change", "coup", "overthrow", "revolution", "transfer of power"},
    "election": {"election", "vote", "ballot", "referendum", "poll"},
    "migration": {"migration", "refugee", "asylum", "displacement", "exodus"},
    "public_health": {"pandemic", "epidemic", "outbreak", "vaccine", "virus", "disease"},

    # Technology
    "ai_breakthrough": {"ai breakthrough", "artificial general", "agi", "large language model", "frontier model"},
    "space_launch": {"launch", "rocket", "mission", "lunar", "mars", "chandrayaan", "artemis"},
    "satellite_deploy": {"satellite", "orbit", "constellation", "spy satellite", "reconnaissance"},

    # Scandal / Diversion
    "political_scandal": {"scandal", "corruption", "leak", "whistleblower", "expose", "files released", "pedophile", "epstein"},
    "disinformation": {"disinformation", "propaganda", "fake news", "information warfare", "narrative"},
    "assassination": {"assassination", "murder", "killed", "targeted killing"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Correlation Templates — predefined inference patterns
# ─────────────────────────────────────────────────────────────────────────────
# Each template defines:
#   - name: human-readable template name
#   - preconditions: list of (domain, event_type) pairs that must co-occur for the same entity cluster
#   - negative_checks: optional events whose ABSENCE strengthens the hypothesis
#   - hypothesis_template: string with {entity} placeholder
#   - severity: default severity level
#   - trust_bonus: additional trust weight when template matches
CORRELATION_TEMPLATES = [
    {
        "name": "Underground Nuclear Test",
        "preconditions": [
            {"domain": "climate", "events": ["earthquake"]},
            {"domain": "defense", "events": ["nuclear_program", "nuclear_test", "missile_test"]},
        ],
        "negative_checks": [
            {"domain": "climate", "events": ["tectonic_activity"]},
        ],
        "title_template": "Suspected Underground Nuclear Test involving {entity} and {actors}",
        "hypothesis_template": "Seismic activity near {entity} combined with an active nuclear program and absence of natural tectonic movement suggests possible underground nuclear testing. Suspected actors responsible: {actors}. Regions involved: {locations}.",
        "severity": "CRIT",
        "trust_bonus": 0.15,
    },
    {
        "name": "Regime Change Operation",
        "preconditions": [
            {"domain": "economics", "events": ["investment", "port_development", "debt_crisis"]},
            {"domain": "society", "events": ["protest", "regime_change"]},
            {"domain": "defense", "events": ["arms_deal", "military_exercise"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Withdrawal of economic support to {entity} coinciding with internal unrest and increased foreign military aid suggests coordinated regime destabilization.",
        "severity": "CRIT",
        "trust_bonus": 0.12,
    },
    {
        "name": "Oil Supply Chain Destabilization",
        "preconditions": [
            {"domain": "geopolitics", "events": ["territorial_dispute", "sanctions", "military_conflict"]},
            {"domain": "economics", "events": ["oil_market", "trade_deal"]},
        ],
        "negative_checks": [],
        "title_template": "Energy Supply Chain Destabilization impacting {entity}",
        "hypothesis_template": "Geopolitical aggression involving {entity} combined with oil market maneuvers suggests a deliberate energy supply chain destabilization strategy. Key Actors: {actors}. Associated Regions: {locations}.",
        "severity": "HIGH",
        "trust_bonus": 0.10,
    },
    {
        "name": "Strategic Diversion Operation",
        "preconditions": [
            {"domain": "society", "events": ["political_scandal"]},
            {"domain": "defense", "events": ["military_conflict", "military_exercise", "arms_deal"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Major political scandal coinciding with military escalation suggests possible strategic diversion — military action used to redirect public attention from {entity}-related controversy.",
        "severity": "HIGH",
        "trust_bonus": 0.08,
    },
    {
        "name": "Economic Coercion Campaign",
        "preconditions": [
            {"domain": "economics", "events": ["sanctions", "trade_deal", "currency_move", "debt_crisis"]},
            {"domain": "geopolitics", "events": ["diplomatic_talks", "territorial_dispute"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Coordinated economic pressure on {entity} alongside diplomatic confrontation indicates a systematic economic coercion campaign.",
        "severity": "HIGH",
        "trust_bonus": 0.08,
    },
    {
        "name": "Military Encirclement",
        "preconditions": [
            {"domain": "defense", "events": ["military_exercise", "arms_deal"]},
            {"domain": "geopolitics", "events": ["treaty", "diplomatic_talks"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Multiple military exercises and arms deals near {entity} combined with new alliance agreements suggest strategic military encirclement.",
        "severity": "HIGH",
        "trust_bonus": 0.10,
    },
    {
        "name": "Cyber-Kinetic Convergence",
        "preconditions": [
            {"domain": "defense", "events": ["cyber_attack"]},
            {"domain": "defense", "events": ["military_exercise", "military_conflict"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Cyber operations targeting {entity} synchronized with conventional military activity suggests hybrid warfare escalation.",
        "severity": "CRIT",
        "trust_bonus": 0.12,
    },
    {
        "name": "Resource Control Play",
        "preconditions": [
            {"domain": "economics", "events": ["investment", "trade_deal", "oil_market"]},
            {"domain": "geopolitics", "events": ["territorial_dispute", "military_conflict"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Territorial aggression near {entity} coupled with resource acquisition moves suggests a deliberate resource control strategy.",
        "severity": "HIGH",
        "trust_bonus": 0.10,
    },
    {
        "name": "Technology Chokepoint Weaponization",
        "preconditions": [
            {"domain": "technology", "events": ["ai_breakthrough", "satellite_deploy"]},
            {"domain": "economics", "events": ["sanctions", "trade_deal"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Technology export restrictions combined with {entity}-related trade actions suggest weaponization of tech supply chain chokepoints.",
        "severity": "HIGH",
        "trust_bonus": 0.08,
    },
    {
        "name": "Humanitarian Crisis Exploitation",
        "preconditions": [
            {"domain": "climate", "events": ["extreme_weather", "earthquake"]},
            {"domain": "society", "events": ["migration", "public_health"]},
            {"domain": "geopolitics", "events": ["diplomatic_talks", "sanctions"]},
        ],
        "negative_checks": [],
        "title_template": "Humanitarian Crisis in {locations} Exploited by {actors}",
        "hypothesis_template": "A natural disaster affecting {entity} has triggered a humanitarian crisis, which is being leveraged as a diplomatic pressure point. Potential exploiting actors: {actors}. Impacted regions: {locations}.",
        "severity": "MED",
        "trust_bonus": 0.06,
    },
    {
        "name": "Alliance Fracture Signal",
        "preconditions": [
            {"domain": "geopolitics", "events": ["diplomatic_talks", "treaty"]},
            {"domain": "economics", "events": ["trade_deal", "sanctions", "currency_move"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Diplomatic re-alignment of {entity} combined with shifting trade patterns indicates fracturing of existing alliance structures.",
        "severity": "MED",
        "trust_bonus": 0.06,
    },
    {
        "name": "Proxy Conflict Escalation",
        "preconditions": [
            {"domain": "defense", "events": ["arms_deal", "military_conflict"]},
            {"domain": "society", "events": ["protest", "regime_change"]},
        ],
        "negative_checks": [],
        "hypothesis_template": "Arms transfers to non-state actors near {entity} combined with civil unrest suggests proxy conflict escalation by external powers.",
        "severity": "CRIT",
        "trust_bonus": 0.12,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Domain classification keywords (maps signals to intelligence domains)
# ─────────────────────────────────────────────────────────────────────────────
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "geopolitics": [
        "diplomacy", "border", "embassy", "treaty", "foreign policy", "summit",
        "minister", "bilateral", "sovereignty", "annex", "territorial",
        "envoy", "ambassador", "sanctions", "alliance", "pact",
    ],
    "economics": [
        "economy", "trade", "gdp", "inflation", "market", "fiscal", "rupee",
        "export", "import", "tariff", "investment", "fdi", "debt", "loan",
        "bailout", "stock", "oil price", "currency", "banking", "imf",
    ],
    "defense": [
        "defense", "military", "army", "navy", "air force", "missile",
        "drone", "war", "cyberattack", "nuclear", "weapon", "strike",
        "troops", "deployment", "exercise", "intelligence", "espionage",
    ],
    "technology": [
        "ai", "artificial intelligence", "llm", "chip", "semiconductor",
        "quantum", "startup", "software", "cyber", "satellite", "space",
        "robot", "computation", "algorithm", "data center",
    ],
    "climate": [
        "climate", "emissions", "renewable", "solar", "heatwave", "flood",
        "drought", "weather", "earthquake", "seismic", "hurricane", "cyclone",
        "wildfire", "glacier", "carbon", "methane",
    ],
    "society": [
        "education", "health", "hospital", "jobs", "welfare", "migration",
        "demography", "culture", "protest", "election", "vote", "scandal",
        "corruption", "refugee", "rights", "freedom",
    ],
}

# Source trust scores for weighted averaging
SOURCE_CREDIBILITY: Dict[str, float] = {
    "reuters": 0.95,
    "associated press": 0.94,
    "bloomberg": 0.92,
    "bbc": 0.90,
    "al jazeera": 0.85,
    "the guardian": 0.87,
    "the hindu": 0.85,
    "times of india": 0.80,
    "ndtv": 0.82,
    "cnbc": 0.85,
    "cnn": 0.82,
    "fox news": 0.65,
    "rt": 0.50,
    "sputnik": 0.45,
    "gnews": 0.75,
    "newsdata": 0.72,
    "reddit": 0.55,
    "twitter": 0.50,
    "x": 0.50,
    "telegram": 0.45,
    "acled": 0.90,
    "gdelt": 0.82,
    "sipri": 0.92,
    "world bank": 0.93,
    "imf": 0.92,
    "default": 0.60,
}


def get_source_credibility(source_name: str) -> float:
    """Get the credibility score for a given source."""
    normalized = (source_name or "").strip().lower()
    for key, score in SOURCE_CREDIBILITY.items():
        if key in normalized:
            return score
    return SOURCE_CREDIBILITY["default"]
