# import requests
# import re
# from collections import defaultdict

# def normalize(text: str):
#     """Normalize text: lowercase, replace separators, and split compound words like smallcap."""
#     text = text.lower()
#     text = text.replace('&', ' ').replace('and', ' ').replace('-', ' ')
#     text = re.sub(r'[()]', ' ', text)
#     text = re.sub(r'(small|mid|large)cap', r'\1 cap', text)  # smallcap → small cap
#     return text

# def get_fund_isins_by_type(search_keyword: str):
#     """
#     Prints and returns ISINs for mutual fund schemes matching:
#     - Exact fund category (like 'small', excluding 'mid', 'large')
#     - Only 'Direct Plan' schemes
#     - Only 'Growth Option' schemes

#     Args:
#         search_keyword (str): Fund category keyword to search (e.g., 'small', 'mid', 'large')

#     Returns:
#         List[str]: List of ISINs matching the filter
#     """
#     url = "https://portal.amfiindia.com/spages/NAVAll.txt"
#     response = requests.get(url)
#     if response.status_code != 200:
#         raise Exception("Failed to fetch data from AMFI")

#     raw_data = response.text
#     lines = raw_data.splitlines()
#     fund_type = None
#     seen_isins = set()
#     matched_isins = []

#     isin_pattern = re.compile(r"INF[0-9A-Z]{9}")
#     search_keyword = search_keyword.lower()

#     for line in lines:
#         line = line.strip()
#         if not line:
#             continue

#         # Detect category
#         if line.startswith("Open Ended Schemes") or line.startswith("Close Ended Schemes"):
#             fund_type = normalize(line)
#             continue

#         # Skip AMC names
#         if "mutual fund" in line.lower():
#             continue

#         # Process fund scheme line
#         if ";" in line and fund_type:
#             parts = line.split(';')
#             if len(parts) < 6:
#                 continue

#             isin_candidates = [parts[1], parts[2], parts[0]]
#             isin = next((i for i in isin_candidates if isin_pattern.match(i)), None)

#             if not isin or isin in seen_isins:
#                 continue

#             scheme_name = parts[3]
#             scheme_name_norm = normalize(scheme_name)

#             # FILTER 1: Only Direct Plan
#             if "direct" not in scheme_name_norm:
#                 continue

#             # FILTER 2: Only Growth Option
#             if "growth" not in scheme_name_norm:
#                 continue

#             # FILTER 3: Match keyword in category or scheme name,
#             # and exclude if mid or large appears in either
#             combined_text = f"{fund_type} {scheme_name_norm}"
#             words = set(combined_text.split())

#             # if (search_keyword in words) and not {'mid', 'large'}.intersection(words):
#             print(f"{isin} --> {scheme_name}")
#             matched_isins.append(isin)
#             seen_isins.add(isin)

#     return matched_isins


# print(get_fund_isins_by_type("large"))