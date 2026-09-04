"""NNDSS Trino lakehouse schema definitions.

Extracted from mcp-for-public-health/agents/nndss-agent/system_prompt.md.
Used for training data generation and prompt construction.
"""

NNDSS_DDL = """\
CREATE TABLE lakehouse.nndss.notifications (
    year INTEGER,
    state VARCHAR,
    disease VARCHAR,
    notifications INTEGER
);
-- Diseases: 'Influenza (laboratory confirmed)', 'Invasive meningococcal disease',
--           'Invasive pneumococcal disease', 'Salmonellosis'
-- Years: 2008-2025
-- States: ACT, NSW, NT, QLD, SA, TAS, VIC, WA

CREATE TABLE lakehouse.nndss.population (
    year INTEGER,
    state VARCHAR,
    population INTEGER
);
-- ABS Estimated Resident Population at 30 June, 2008-2025

CREATE TABLE lakehouse.nndss.fortnightly_notifications (
    year INTEGER,
    period_start VARCHAR,
    period_end VARCHAR,
    disease_group VARCHAR,
    disease VARCHAR,
    state VARCHAR,
    notifications INTEGER
);
-- 73 notifiable diseases, 2024-2026, fortnightly reporting
-- Disease groups: Bloodborne, Gastrointestinal, Respiratory,
--   Sexually transmissible, Vaccine preventable, Vectorborne, Zoonoses, Other
"""

DISEASES = [
    "Influenza (laboratory confirmed)",
    "Invasive meningococcal disease",
    "Invasive pneumococcal disease",
    "Salmonellosis",
]

STATES = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]

YEARS = list(range(2008, 2026))

DISEASE_GROUPS = [
    "Bloodborne", "Gastrointestinal", "Respiratory",
    "Sexually transmissible", "Vaccine preventable",
    "Vectorborne", "Zoonoses", "Other",
]

SQL_PATTERNS = {
    "simple_lookup": (
        "How many {disease} notifications were there in {state} in {year}?",
        "SELECT notifications FROM lakehouse.nndss.notifications "
        "WHERE disease = '{disease}' AND state = '{state}' AND year = {year}"
    ),
    "aggregation": (
        "What was the total number of {disease} notifications across all states in {year}?",
        "SELECT SUM(notifications) as total FROM lakehouse.nndss.notifications "
        "WHERE disease = '{disease}' AND year = {year}"
    ),
    "per_capita_join": (
        "What was the {disease} notification rate per 100,000 population in {state} for {year}?",
        "SELECT n.notifications, p.population, "
        "ROUND(100000.0 * n.notifications / p.population, 1) AS rate_per_100k "
        "FROM lakehouse.nndss.notifications n "
        "JOIN lakehouse.nndss.population p ON n.state = p.state AND n.year = p.year "
        "WHERE n.disease = '{disease}' AND n.state = '{state}' AND n.year = {year}"
    ),
    "comparison": (
        "Which state had the highest {disease} notifications in {year}?",
        "SELECT state, notifications FROM lakehouse.nndss.notifications "
        "WHERE disease = '{disease}' AND year = {year} "
        "ORDER BY notifications DESC LIMIT 1"
    ),
    "trend": (
        "Show {disease} notification trends from {year1} to {year2}.",
        "SELECT year, SUM(notifications) as total FROM lakehouse.nndss.notifications "
        "WHERE disease = '{disease}' AND year BETWEEN {year1} AND {year2} "
        "GROUP BY year ORDER BY year"
    ),
    "cross_disease": (
        "Compare all disease notifications in {state} for {year}.",
        "SELECT disease, notifications FROM lakehouse.nndss.notifications "
        "WHERE state = '{state}' AND year = {year} ORDER BY notifications DESC"
    ),
    "subquery": (
        "In the most recent year of data, which state had the lowest {disease} notifications?",
        "SELECT state, notifications FROM lakehouse.nndss.notifications "
        "WHERE disease = '{disease}' "
        "AND year = (SELECT MAX(year) FROM lakehouse.nndss.notifications WHERE disease = '{disease}') "
        "ORDER BY notifications ASC LIMIT 1"
    ),
    "per_capita_ranking": (
        "Rank all states by {disease} notification rate per 100,000 in {year}.",
        "SELECT n.state, n.notifications, p.population, "
        "ROUND(100000.0 * n.notifications / p.population, 1) AS rate_per_100k "
        "FROM lakehouse.nndss.notifications n "
        "JOIN lakehouse.nndss.population p ON n.state = p.state AND n.year = p.year "
        "WHERE n.disease = '{disease}' AND n.year = {year} "
        "ORDER BY rate_per_100k DESC"
    ),
}
