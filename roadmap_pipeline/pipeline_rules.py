"""Sanitized transformation rules extracted from the working Roadmunk-to-ServiceNow pipeline.
No tokens, URLs for notifications, Roadmunk IDs, or GraphQL operations are included.
"""
import html
import re
from urllib.parse import quote
import pandas as pd

SERVICENOW_BASE_URL = "https://utsystem.service-now.com"
PROJECT_ENDPOINT = "pm_project"
DEMAND_ENDPOINT = "dmn_demand"
ENHANCEMENT_ENDPOINT = "rm_enhancement"
IDEA_ENDPOINT = "idea"
STATE_TO_STATUS = {
    "Work in Progress":"Work in Progress", "Open":"Open", "Pending":"Pending",
    "Closed Complete":"Closed Complete", "Closed Incomplete":"Closed Incomplete",
    "Closed Skipped":"Closed Skipped", "Scoping":"Work in Progress",
}

def is_blank(value):
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"", "nan", "nat", "none", "null"}


def clean_text(value):
    if is_blank(value):
        return ""
    return " ".join(html.unescape(str(value)).replace('"', "").strip().split())


def get_latest_file(pattern):
    files = [p for p in glob.glob(pattern) if not os.path.basename(p).startswith("~$")]
    if not files:
        raise FileNotFoundError(f"No files found matching: {pattern}")
    return max(files, key=os.path.getmtime)


def get_col(df, options):
    return next((column for column in options if column in df.columns), None)


def safe_series(df, column, default=""):
    if column and column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def normalize_date(value):
    if is_blank(value):
        return ""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            dt = pd.Timestamp("1899-12-30") + pd.to_timedelta(float(value), unit="D")
        else:
            dt = pd.to_datetime(value, errors="coerce")
        return "" if pd.isna(dt) else dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def derive_fy_from_date(value):
    if is_blank(value):
        return ""
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    fy = dt.year + 1 if dt.month >= 7 else dt.year
    return f"FY{str(fy)[-2:]}"


def format_fy(value, end_date):
    text = clean_text(value).upper()
    return text if text.startswith("FY") else derive_fy_from_date(end_date)


def normalize_percent(value):
    if is_blank(value):
        return "0"
    try:
        return str(int(float(str(value).replace("%", "").strip())))
    except Exception:
        return "0"


def normalize_active(value):
    """Preserve Roadmunk list choices as True/False while accepting common source variants."""
    if is_blank(value):
        return ""
    text = clean_text(value).casefold()
    if text in {"true", "1", "yes", "y", "active"}:
        return "True"
    if text in {"false", "0", "no", "n", "inactive"}:
        return "False"
    return clean_text(value)


def split_raw_values(value):
    if is_blank(value):
        return []
    return [clean_text(part) for part in str(value).split(",") if clean_text(part)]


def normalize_pillar_name(value):
    text = clean_text(value).upper()
    if not text or text in {"CROSS-PILLAR", "CROSS PILLAR", "CROSSPILLAR"}:
        return ""
    mapping = {
        "OTISCS": ["OTISCS", "OTIS-CS"],
        "OTIS": ["TECH INFOR", "TECH INFO", "OTIS", "TECH INFOR SERVICES", "TECH INFO SERVICES", "TECH AND INFO SERVICES"],
        "ISO": ["INFORMATION SECURITY", "ISO", "INFORMATION SECURITY OFFICE"],
        "B&CS": ["B&CS", "B & CS", "SHARED INFORMATION"],
        "IAS": ["IAS", "INTELLIGENT AUTOMATION SERVICES"],
        "SWIS": ["SWIS", "SYSTEMWIDE INFO SERVICES"],
        "FMS": ["FMS"], "HCM": ["HCM"], "ARDC": ["ARDC"], "BI": ["BI"],
        "PMO": ["PMO"], "CS": ["CS"],
        "SIS SERVICES": ["SIS", "SHARED INFORMATION SERVICES"],
        "ARC": ["ARC", "ACCOUNTING RESOURCE CENTER"],
    }
    for acronym, variations in mapping.items():
        if text in variations:
            return acronym
    return text


def service_now_link(endpoint, number):
    endpoint = endpoint.removesuffix(".do")
    return f"{SERVICENOW_BASE_URL}/{endpoint}.do?sysparm_query=number={quote(str(number).strip())}"


def get_description(number, source_df, description_column, endpoint):
    raw = ""
    if description_column and "Number" in source_df.columns:
        mask = source_df["Number"].fillna("").astype(str).str.strip() == str(number).strip()
        matches = source_df.loc[mask, description_column]
        if not matches.empty:
            raw = clean_text(matches.iloc[0])
    link = service_now_link(endpoint, number)
    parts = [html.escape(raw)] if raw else []
    parts.append(f"Project Link: <a href='{html.escape(link, quote=True)}' target='_blank'>Open in ServiceNow</a>")
    return "<br><br>".join(parts)


def validate_fields_map():
    blank_keys = [key for key, value in FIELDS_MAP.items() if not clean_text(value)]
    if blank_keys:
        raise ValueError("Blank Roadmunk field IDs: " + ", ".join(blank_keys))

    id_to_keys = {}
    for key, field_id in FIELDS_MAP.items():
        id_to_keys.setdefault(field_id, []).append(key)
    duplicates = {field_id: keys for field_id, keys in id_to_keys.items() if len(keys) > 1}
    if duplicates:
        details = "; ".join(f"{field_id}: {', '.join(keys)}" for field_id, keys in duplicates.items())
        raise ValueError("FIELDS_MAP contains duplicate Roadmunk IDs: " + details)


def get_row_hash(row_dict):
    keys = [
        "Status", "Risk", "Active", "Pillar", "Project Manager", "% Complete",
        "Raw_Title", "Start Date", "End Date", "Description_Raw", "Campus",
        "Functional Committee", "Teams", "Focus Area", "Type",
        "Cleaned_Fiscal_Year_Value",
    ]
    data = {key: str(row_dict.get(key, "")) for key in keys}
    return hashlib.md5(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def log_error(external_id, operation, message, payload=None):
    exists = os.path.exists(ERROR_LOG_FILE)
    with open(ERROR_LOG_FILE, "a", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        if not exists:
            writer.writerow(["Timestamp", "External_ID", "Operation", "Message", "Payload"])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"), external_id, operation, message,
            json.dumps(payload or {}, ensure_ascii=False, default=str),
        ])


def audit_payload(external_id, operation, payload):
    with open(PAYLOAD_AUDIT_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "external_id": external_id,
            "operation": operation,
            "payload": payload,
        }, ensure_ascii=False, default=str) + "\n")


# ============================================================
# 3. SOURCE PROCESSORS
# ============================================================
def process_df(df, record_type="Project"):
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Only the Projects export uses source Status as Risk.
    rename_map = {
        "Project manager": "Project Manager",
        "Impacted Companies": "Campus",
        "Assignment group": "Teams",
        "Investment Type": "Focus Area",
    }
    if record_type == "Project" and "Status" in df.columns:
        rename_map["Status"] = "Risk"
    df = df.rename(columns=rename_map)

    if "Number" not in df.columns:
        raise ValueError(f"{record_type} file is missing required column: Number")

    endpoint = {"Project": "pm_project", "Demand": "dmn_demand", "Enhancement": "rm_enhancement"}[record_type]
    out = pd.DataFrame(index=df.index)
    out["SN Project Number"] = df["Number"].fillna("").astype(str).str.strip()
    out["Original ID"] = out["SN Project Number"]
    out["Type"] = record_type

    title_col = get_col(df, ["Project Name", "Title", "Name", "Short description", "Short Description"])
    out["Raw_Title"] = safe_series(df, title_col, "No summary").fillna("No summary").astype(str).str.strip()

    if record_type == "Enhancement":
        starts = safe_series(df, get_col(df, ["Actual start date", "Actual Start date"]), pd.NA).combine_first(
            safe_series(df, get_col(df, ["Planned start date", "Planned Start date"]), pd.NA)
        )
        ends = safe_series(df, get_col(df, ["Actual end date", "Actual End date"]), pd.NA).combine_first(
            safe_series(df, get_col(df, ["Planned end date", "Planned End date"]), pd.NA)
        )
    else:
        starts = safe_series(df, get_col(df, ["Approved start date", "Planned start date", "Start date", "Desired Start date"]), pd.NA)
        ends = safe_series(df, get_col(df, ["Approved end date", "Planned end date", "End date", "Desired End date"]), pd.NA)

    out["Start Date"] = starts.apply(normalize_date)
    out["End Date"] = ends.apply(normalize_date)
    out["% Complete"] = df["Percent complete"].apply(normalize_percent) if "Percent complete" in df.columns else "0"
    out["Cleaned_Fiscal_Year_Value"] = (
        [format_fy(value, end_date) for value, end_date in zip(df["Fiscal Year"], out["End Date"])]
        if "Fiscal Year" in df.columns else out["End Date"].apply(derive_fy_from_date)
    )

    source_fields = {
        "Campus": ["Campus"],
        "Teams": ["Teams", "Assignment Group"],
        "Functional Committee": ["Portfolio", "Functional Committee", "Portfolio Name"],
        "Project Manager": ["Project Manager"],
    }
    sysid_pattern = re.compile(r"^[a-fA-F0-9]{32}$")
    for target, candidates in source_fields.items():
        values = safe_series(df, get_col(df, candidates), "").fillna("").astype(str).str.strip()
        out[target] = values.apply(lambda value: "" if sysid_pattern.fullmatch(value) else value)

    out["Teams"] = out["Teams"].str.upper()
    out["Functional Committee"] = out["Functional Committee"].str.upper()
    out["Focus Area"] = ""

    if record_type == "Enhancement":
        assigned = get_col(df, ["Assigned to", "Assigned To"])
        if assigned:
            out["Project Manager"] = safe_series(df, assigned, "").fillna("").astype(str).str.strip()

    # Risk and Active apply only to Projects. Other record types remain blank.
    if record_type == "Project":
        out["Risk"] = safe_series(df, "Risk", "").fillna("").astype(str).str.strip()
        out["Active"] = safe_series(df, "Active", "").apply(normalize_active)
    else:
        out["Risk"] = ""
        out["Active"] = ""

    dept_col = get_col(df, ["Department", "Department_Raw", "Owning Department"])
    impacted_col = get_col(df, ["Impacted Pillars", "Impacted pillars", "Pillars Impacted"])
    out["Department_Raw"] = safe_series(df, dept_col, "").fillna("").astype(str).str.strip().str.upper()
    out["Originating Pillar"] = out["Department_Raw"].apply(normalize_pillar_name)
    out["Impacted_List"] = (
        safe_series(df, impacted_col, "").apply(
            lambda value: [name for name in (normalize_pillar_name(item) for item in split_raw_values(value)) if name]
        ) if impacted_col else [[] for _ in range(len(out))]
    )
    out["Impacted_List"] = out["Impacted_List"].apply(lambda values: values or [""])
    out = out.explode("Impacted_List").drop_duplicates(subset=["SN Project Number", "Impacted_List"])
    out["Pillar"] = out["Impacted_List"].where(
        out["Impacted_List"].fillna("").astype(str).str.strip().ne(""), out["Originating Pillar"]
    )
    blank = out["Pillar"].fillna("").astype(str).str.strip().eq("")
    out.loc[blank, ["Originating Pillar", "Pillar"]] = "OTIS"

    ias = out["Functional Committee"].fillna("").astype(str).str.contains(
        "INTELLIGENT AUTOMATION SERVICES", case=False, na=False
    )
    out.loc[ias, ["Department_Raw", "Originating Pillar", "Pillar"]] = "IAS"
    out.loc[ias, "Teams"] = "IAS - INTELLIGENT AUTOMATION SERVICES"
    arc = out["Department_Raw"].fillna("").astype(str).str.strip().str.upper().isin(["ARC", "ACCOUNTING RESOURCE CENTER"])
    out.loc[arc, ["Functional Committee", "Originating Pillar", "Pillar"]] = "ARC"

    def build_title(row):
        title = clean_text(row["Raw_Title"]) or "No summary"
        pillar = clean_text(row["Pillar"]).upper()
        origin = clean_text(row["Originating Pillar"]).upper()
        display = "SIS Service" if origin.replace(" ", "") == "B&CS" else origin
        return f"{title} ***{display}***" if pillar and pillar != origin and pillar != "OCIO" else title

    out["Item (REQUIRED)"] = out.apply(build_title, axis=1)
    desc_col = get_col(df, ["Description", "Short description", "Short Description", "Notes"])
    descriptions = {
        number: get_description(number, df, desc_col, endpoint)
        for number in df["Number"].fillna("").astype(str).str.strip().unique()
    }
    out["Description_Raw"] = out["SN Project Number"].map(descriptions).fillna("")
    out["Cleaned_Area_List"] = ""

    # Project lifecycle Status comes from State, never from source Status/Risk.
    status_col = get_col(df, ["State", "state"])
    statuses = (
        dict(zip(
            df["Number"].fillna("").astype(str).str.strip(),
            df[status_col].fillna("").astype(str).str.strip(),
        )) if status_col else {}
    )

    if record_type == "Project":
        raw_status = out["SN Project Number"].map(statuses)
        unknown = sorted({clean_text(value) for value in raw_status if not is_blank(value) and clean_text(value) not in STATE_TO_STATUS})
        if unknown:
            raise ValueError("Unrecognized Project State value(s): " + ", ".join(unknown))
        out["Status"] = raw_status.map(STATE_TO_STATUS).fillna("Open")
    elif record_type == "Demand":
        out["Status"] = "Demand"
    else:
        out["Status"] = out["SN Project Number"].map(statuses).fillna("").str.lower().apply(
            lambda value: "Closed Complete" if value == "closed complete" else "Enhancement"
        )

    out["External ID"] = out["SN Project Number"].astype(str) + "_" + out["Pillar"].astype(str)
    return out.reset_index(drop=True)


def process_ideas_df(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    required = [
        "Number", "Title", "Department", "Portfolio", "Submitted by",
        "Interested Companies", "Created", "Implementation Deadline", "State",
        "Idea Development Escalation",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Ideas file is missing required columns: " + ", ".join(missing))

    out = pd.DataFrame(index=df.index)
    out["SN Project Number"] = df["Number"].fillna("").astype(str).str.strip()
    out["Original ID"] = out["SN Project Number"]
    out["Type"] = "Idea"
    out["Status"] = "Idea"
    out["Idea State"] = df["State"].fillna("").astype(str).str.strip()
    out["Implementation Date"] = df["Implementation Deadline"].apply(normalize_date)
    out["Risk"] = ""
    out["Active"] = ""
    out["Raw_Title"] = df["Title"].fillna("No summary").astype(str).str.strip()
    out["Item (REQUIRED)"] = out["Raw_Title"].apply(lambda value: clean_text(value) or "No summary")
    out["Department_Raw"] = df["Department"].fillna("").astype(str).str.strip().str.upper()
    out["Originating Pillar"] = out["Department_Raw"].apply(normalize_pillar_name)
    out["Pillar"] = out["Originating Pillar"]
    out["Functional Committee"] = df["Portfolio"].fillna("").astype(str).str.strip().str.upper()
    out["Project Manager"] = df["Submitted by"].fillna("").astype(str).str.strip()
    out["Campus"] = df["Interested Companies"].fillna("").astype(str).str.strip().str.upper()
    out["Teams"] = ""
    out["Focus Area"] = ""
    dates = pd.to_datetime(df["Created"], errors="coerce") + pd.Timedelta(days=90)
    out["Start Date"] = dates.dt.strftime("%Y-%m-%d").fillna("")
    out["End Date"] = out["Start Date"]
    out["% Complete"] = "0"
    out["Cleaned_Fiscal_Year_Value"] = out["End Date"].apply(derive_fy_from_date)
    out["Cleaned_Area_List"] = ""

    swis = out["Department_Raw"].eq("SWIS")
    out.loc[swis, ["Functional Committee", "Pillar", "Originating Pillar"]] = "SWIS"
    ias = out["Functional Committee"].str.contains("INTELLIGENT AUTOMATION SERVICES", case=False, na=False)
    out.loc[ias, ["Department_Raw", "Originating Pillar", "Pillar"]] = "IAS"
    arc = out["Department_Raw"].isin(["ARC", "ACCOUNTING RESOURCE CENTER"])
    out.loc[arc, ["Functional Committee", "Originating Pillar", "Pillar"]] = "ARC"

    def description(index):
        number = clean_text(df.at[index, "Number"])
        title = clean_text(df.at[index, "Title"])
        escalation = clean_text(df.at[index, "Idea Development Escalation"])
        link = service_now_link(IDEA_ENDPOINT, number)
        return "<br><br>".join([
            f"Title: {html.escape(title)}",
            f"Idea Development Escalation: {html.escape(escalation)}",
            f"Idea Link: <a href='{html.escape(link, quote=True)}' target='_blank'>Open in ServiceNow</a>",
        ])

    out["Description_Raw"] = [description(index) for index in df.index]
    out["External ID"] = out["SN Project Number"].astype(str) + "_" + out["Pillar"].astype(str)
    return out.reset_index(drop=True)


# ============================================================
# 4. GRAPHQL, REGISTRY, AND PM CHOICE HELPERS
# ============================================================
CREATE_ITEM_MUTATION = """mutation CreateItem($roadmapID: ID!, $summary: String!, $startDate: Day, $endDate: Day, $description: String, $fields: [ItemFieldInput!]) { createItem(roadmapID: $roadmapID, summary: $summary, startDate: $startDate, endDate: $endDate, description: $description, fields: $fields) { id } }"""
UPDATE_ITEM_MUTATION = """mutation UpdateItem($itemID: ID!, $summary: String!, $startDate: Day, $endDate: Day, $description: String, $fields: [ItemFieldInput!]) { updateItem(itemID: $itemID, summary: $summary, startDate: $startDate, endDate: $endDate, description: $description, fields: $fields) { id } }"""
DELETE_ITEM_MUTATION = """mutation DeleteItems($itemIDs: [ID!]!) { deleteItems(itemIDs: $itemIDs) { id } }"""

