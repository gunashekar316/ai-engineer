import json
from pathlib import Path

def get_intent(s):
    if not s: return "general"
    s = s.lower()
    if "住民税" in s: return "resident_tax"
    if "給与" in s or "控除" in s: return "salary_maintenance"
    if "育児" in s or "産休" in s: return "childcare_leave"
    if "社保" in s or "年金" in s: return "social_insurance"
    if "入社" in s or "手当" in s: return "onboarding_allowance"
    if "請求書" in s: return "invoice_approval"
    if "経費" in s or "精算" in s: return "expense_claim"
    if "銀行" in s or "勘定" in s or "照合" in s: return "bank_reconciliation"
    if "予算" in s or "差異" in s: return "budget_variance"
    if "支払" in s: return "payment_processing"
    if "受注" in s: return "order_processing"
    if "在庫" in s: return "inventory_adjustment"
    if "仕入先" in s: return "supplier_contact"
    if "出荷" in s or "追跡" in s: return "shipment_tracking"
    if "返品" in s: return "return_processing"
    
    if "承認" in s: return "approve"
    if "申請" in s: return "apply"
    if "保存" in s: return "save"
    if "検索" in s: return "search"
    if "差戻" in s or "却下" in s: return "reject"
    if "確定" in s or "確認" in s: return "confirm"
    return "general"

def populate_translation_map():
    script_dir = Path(__file__).resolve().parent
    extracted_path = script_dir / "extracted_ui_elements.json"
    with open(extracted_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    apps = data.get("window_and_app_names", [])
    urls = data.get("browser_urls_and_titles", [])
    labels = data.get("ui_element_attributes", [])
    
    apps_map = {}
    urls_map = {}
    labels_map = {}
    
    for app in apps:
        app_lower = app.lower()
        cat = "utility"
        if "chrome" in app_lower or "edge" in app_lower or "firefox" in app_lower or "browser" in app_lower:
            cat = "browser"
        elif "excel" in app_lower or "スプレッドシート" in app_lower or "spreadsheet" in app_lower or ".xlsx" in app_lower or ".csv" in app_lower:
            cat = "spreadsheet"
        elif "word" in app_lower or "notepad" in app_lower or "pdf" in app_lower or "document" in app_lower or "ドキュメント" in app_lower:
            cat = "document"
        elif "portal" in app_lower or "ポータル" in app_lower or "erp" in app_lower or "システム" in app_lower:
            cat = "portal"
            
        apps_map[app] = {"app_category": cat, "inferred_intent": get_intent(app)}
            
    for url in urls:
        url_l = url.lower()
        dom = "general"
        if "hr" in url_l or "human" in url_l or "staff" in url_l or "employee" in url_l or "jinji" in url_l or "kyuyo" in url_l:
            dom = "hr"
        elif "finance" in url_l or "accounting" in url_l or "invoice" in url_l or "bank" in url_l or "keiri" in url_l or "zaimu" in url_l:
            dom = "finance"
        elif "ops" in url_l or "operations" in url_l or "inventory" in url_l or "logistics" in url_l or "order" in url_l or "zaiko" in url_l:
            dom = "operations"
        elif "login" in url_l or "auth" in url_l or "sso" in url_l:
            dom = "system"
            
        urls_map[url] = {"domain": dom, "inferred_intent": get_intent(url)}
            
    for label in labels:
        labels_map[label] = {"inferred_intent": get_intent(label)}
            
    translation_map = {
        "apps_and_windows": apps_map,
        "urls": urls_map,
        "ui_labels": labels_map
    }
    
    out_path = script_dir / "src" / "segmentation" / "translation_map.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(translation_map, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    populate_translation_map()
