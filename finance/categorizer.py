"""Auto-categorization using regex pattern matching against transaction narrations."""
import re

# ── Built-in rules (highest priority first) ──
DEFAULT_RULES = [
    (r'salary|wages|payroll|stipend', 'Salary'),
    (r'rent|maintenance|society|housing|pg\b|hostel', 'Rent & Housing'),
    (r'emi\b|loan|interest|repayment|hdfc.*loan|bajaj.*fin', 'Loan & EMI'),
    (r'insurance|lic|health|mediclaim|star.*health|icici.*pru', 'Insurance'),
    (r'swiggy|zomato|food|restaurant|cafe|dominos|mcd|pizza|burger', 'Food & Dining'),
    (r'uber|ola|taxi|cab|metro|fuel|petrol|diesel|parking|toll|rapido', 'Transport'),
    (r'amazon|flipkart|myntra|ajio|shopping|meesho|nykaa|decathlon', 'Shopping'),
    (r'electricity|water|gas|broadband|wifi|jio|airtel|vi\b|bsnl|tata.*sky', 'Utilities'),
    (r'netflix|spotify|hotstar|prime|youtube|subscription|apple', 'Subscriptions'),
    (r'pharma|medical|hospital|apollo|medplus|1mg|practo', 'Healthcare'),
    (r'gym|fitness|cult\.fit|yoga|sports', 'Fitness'),
    (r'transfer|upi|neft|imps|rtgs|self', 'Transfers'),
    (r'atm|cash|withdrawal', 'Cash Withdrawal'),
    (r'dividend|mutual.*fund|sip|zerodha|groww|stock|invest', 'Investments'),
    (r'education|course|udemy|coursera|tuition|school|college', 'Education'),
]


def categorize(text: str) -> str:
    """
    Categorize a narration/description string.
    1. Check built-in regex rules
    2. Check database CategoryRules (lazy import to avoid circular)
    3. Fall back to 'Uncategorized'
    """
    text_lower = text.strip().lower()

    # Check built-in rules
    for pattern, category in DEFAULT_RULES:
        if re.search(pattern, text_lower):
            return category

    # Check database rules
    try:
        from finance.models import CategoryRule
        for rule in CategoryRule.objects.all():
            if re.search(rule.pattern, text_lower, re.IGNORECASE):
                return rule.category
    except Exception:
        pass

    return 'Uncategorized'
