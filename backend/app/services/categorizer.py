INCOME_CATEGORIES = ["Freelance Income", "Salary", "Affiliate Income", "Business Revenue", "Refunds"]
EXPENSE_CATEGORIES = [
    "Software",
    "Marketing",
    "Food",
    "Travel",
    "Office",
    "Education",
    "Utilities",
    "Personal",
    "Miscellaneous",
]

KEYWORD_CATEGORY_MAP = {
    "STARBUCKS": "Food",
    "SWIGGY": "Food",
    "ZOMATO": "Food",
    "CAFE": "Food",
    "LINKEDIN ADS": "Marketing",
    "META ADS": "Marketing",
    "GOOGLE ADS": "Marketing",
    "FIGMA": "Software",
    "GOOGLE CLOUD": "Software",
    "AWS": "Software",
    "VERCEL": "Software",
    "ADOBE": "Software",
    "UBER": "Travel",
    "OLA": "Travel",
    "MAKEMYTRIP": "Travel",
    "COURSERA": "Education",
    "UDEMY": "Education",
    "ELECTRICITY": "Utilities",
    "AIRTEL": "Utilities",
    "JIO": "Utilities",
    "RENT": "Office",
    "STATIONERY": "Office",
}

INCOME_KEYWORDS = {
    "UPWORK": "Freelance Income",
    "FREELANCE": "Freelance Income",
    "CLIENT": "Business Revenue",
    "INVOICE": "Business Revenue",
    "SALARY": "Salary",
    "AFFILIATE": "Affiliate Income",
    "REFUND": "Refunds",
}


def categorize_transaction(description: str, transaction_type: str) -> str:
    normalized = description.upper()
    if transaction_type == "income":
        for keyword, category in INCOME_KEYWORDS.items():
            if keyword in normalized:
                return category
        return "Business Revenue"

    for keyword, category in KEYWORD_CATEGORY_MAP.items():
        if keyword in normalized:
            return category
    return "Miscellaneous"
