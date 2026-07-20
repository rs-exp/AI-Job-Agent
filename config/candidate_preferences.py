"""
Candidate-specific preferences used by suitability scoring.

Role relevance determines whether a job belongs to a target career
category. Candidate suitability determines whether that relevant job
is realistically appropriate for this candidate.
"""


PREFERRED_LOCATIONS = (
    "pune",
    "mumbai",
    "maharashtra",
)


HOME_COUNTRY_KEYWORDS = (
    "india",
    "ind",
)


WORK_MODE_PRIORITY = {
    "remote": 3,
    "hybrid": 2,
    "in_office": 1,
}


TARGET_ROLE_PRIORITY = {
    "cloud_support": 6,
    "cloud_operations": 5,
    "production_support": 4,
    "devops": 3,
    "sre": 2,
    "platform_engineering": 1,
}


TARGET_TECHNOLOGY_GROUPS = (
    "cloud",
    "systems",
    "monitoring",
    "devops_tools",
    "containers",
)


PREFERRED_TECHNOLOGY_KEYWORDS = (
    "azure",
    "aws",
    "amazon web services",
    "microsoft 365",
    "office 365",
    "m365",
    "linux",
    "windows server",
    "networking",
    "dns",
    "load balancer",
    "firewall",
    "virtual machine",
    "azure monitor",
    "cloudwatch",
    "incident management",
    "terraform",
    "ansible",
    "docker",
    "kubernetes",
)


EXCLUDED_SENIORITY_KEYWORDS = (
    "principal",
    "director",
    "head of",
    "vice president",
    "vp ",
)


HIGH_SENIORITY_KEYWORDS = (
    "staff",
    "lead",
    "architect",
)


PREFERRED_SENIORITY_KEYWORDS = (
    "engineer",
    "associate",
    "specialist",
    "administrator",
    "l2",
    "l3",
)


JUNIOR_OR_TRAINING_KEYWORDS = (
    "intern",
    "internship",
    "trainee",
    "apprentice",
)


CURRENT_CTC_LPA = 8.65
EXPECTED_CTC_LPA = 15.0

NOTICE_PERIOD_END_DATE = "2026-09-01"