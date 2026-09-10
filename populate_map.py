import json
from pathlib import Path

def populate_translation_map():
    # Load extracted elements
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
    
    # Keyword rules for apps
    for app in apps:
        app_lower = app.lower()
        if "chrome" in app_lower or "edge" in app_lower or "firefox" in app_lower or "browser" in app_lower:
            apps_map[app] = "browser"
        elif "excel" in app_lower or "スプレッドシート" in app_lower or "spreadsheet" in app_lower or ".xlsx" in app_lower or ".csv" in app_lower:
            apps_map[app] = "spreadsheet"
        elif "word" in app_lower or "notepad" in app_lower or "pdf" in app_lower or "document" in app_lower or "ドキュメント" in app_lower:
            apps_map[app] = "document"
        elif "portal" in app_lower or "ポータル" in app_lower or "erp" in app_lower or "システム" in app_lower:
            apps_map[app] = "portal"
        else:
            apps_map[app] = "utility"
            
    # Keyword rules for URLs
    for url in urls:
        if "hr" in url.lower() or "human" in url.lower() or "staff" in url.lower() or "employee" in url.lower() or " personnel" in url.lower() or "jinji" in url.lower() or "kyuyo" in url.lower():
            urls_map[url] = "hr"
        elif "finance" in url.lower() or "accounting" in url.lower() or "invoice" in url.lower() or "bank" in url.lower() or "keiri" in url.lower() or "zaimu" in url.lower():
            urls_map[url] = "finance"
        elif "ops" in url.lower() or "operations" in url.lower() or "inventory" in url.lower() or "logistics" in url.lower() or "order" in url.lower() or "zaiko" in url.lower():
            urls_map[url] = "operations"
        elif "login" in url.lower() or "auth" in url.lower() or "sso" in url.lower():
            urls_map[url] = "system"
        else:
            urls_map[url] = "general"
            
    # Keyword rules for UI labels
    for label in labels:
        # Match process intents
        if "住民税" in label: labels_map[label] = "resident_tax"
        elif "給与" in label or "控除" in label: labels_map[label] = "salary_maintenance"
        elif "育児" in label or "産休" in label: labels_map[label] = "childcare_leave"
        elif "社保" in label or "年金" in label: labels_map[label] = "social_insurance"
        elif "入社" in label or "手当" in label: labels_map[label] = "onboarding_allowance"
        elif "請求書" in label: labels_map[label] = "invoice_approval"
        elif "経費" in label or "精算" in label: labels_map[label] = "expense_claim"
        elif "銀行" in label or "勘定" in label or "照合" in label: labels_map[label] = "bank_reconciliation"
        elif "予算" in label or "差異" in label: labels_map[label] = "budget_variance"
        elif "支払" in label: labels_map[label] = "payment_processing"
        elif "受注" in label: labels_map[label] = "order_processing"
        elif "在庫" in label: labels_map[label] = "inventory_adjustment"
        elif "仕入先" in label: labels_map[label] = "supplier_contact"
        elif "出荷" in label or "追跡" in label: labels_map[label] = "shipment_tracking"
        elif "返品" in label: labels_map[label] = "return_processing"
        # Match generic action intents
        elif "承認" in label: labels_map[label] = "approve"
        elif "申請" in label: labels_map[label] = "apply"
        elif "保存" in label: labels_map[label] = "save"
        elif "検索" in label: labels_map[label] = "search"
        elif "差戻" in label or "却下" in label: labels_map[label] = "reject"
        elif "確定" in label or "確認" in label: labels_map[label] = "confirm"
        else:
            labels_map[label] = "general"
            
    translation_map = {
        "apps_and_windows": apps_map,
        "urls": urls_map,
        "ui_labels": labels_map
    }
    
    out_path = script_dir / "src" / "segmentation" / "translation_map.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(translation_map, f, ensure_ascii=False, indent=2)
        
    print(f"Populated translation_map.json:")
    print(f" - Apps/Windows: {len(apps_map)}")
    print(f" - URLs: {len(urls_map)}")
    print(f" - UI Labels: {len(labels_map)}")

if __name__ == '__main__':
    populate_translation_map()
