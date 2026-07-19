"""
Rules used by Job Relevance Filtering v0.1.

These rules are intentionally separate from the filtering logic so
they can be adjusted without rewriting the service.
"""


TARGET_ROLE_GROUPS = {
    "devops": {
        "weight": 10,
        "keywords": (
            "devops engineer",
            "devops",
            "ci/cd engineer",
            "continuous integration",
            "continuous deployment",
        ),
    },
    "sre": {
        "weight": 10,
        "keywords": (
            "site reliability engineer",
            "site reliability",
            "sre engineer",
            "sre",
            "reliability engineer",
        ),
    },
    "cloud_operations": {
        "weight": 9,
        "keywords": (
            "cloud operations engineer",
            "cloud operations",
            "cloud engineer",
            "cloud infrastructure engineer",
            "cloud administrator",
            "cloud platform engineer",
        ),
    },
    "cloud_support": {
        "weight": 8,
        "keywords": (
            "cloud support engineer",
            "azure support engineer",
            "aws support engineer",
            "cloud technical support",
            "cloud support specialist",
            "technical support engineer",
        ),
    },
    "platform_engineering": {
        "weight": 8,
        "keywords": (
            "platform engineer",
            "platform operations engineer",
            "infrastructure engineer",
            "systems engineer",
            "production engineer",
        ),
    },
    "production_support": {
        "weight": 6,
        "keywords": (
            "production support engineer",
            "application support engineer",
            "technical operations engineer",
            "operations support engineer",
            "l2 support engineer",
            "l3 support engineer",
        ),
    },
}


TECHNOLOGY_KEYWORDS = {
    "cloud": {
        "weight": 3,
        "keywords": (
            "azure",
            "amazon web services",
            "aws",
            "cloud infrastructure",
            "cloud computing",
            "microsoft 365",
            "office 365",
        ),
    },
    "devops_tools": {
        "weight": 3,
        "keywords": (
            "terraform",
            "ansible",
            "jenkins",
            "github actions",
            "azure devops",
            "gitlab ci",
            "ci/cd",
        ),
    },
    "containers": {
        "weight": 3,
        "keywords": (
            "docker",
            "kubernetes",
            "aks",
            "eks",
            "containerization",
        ),
    },
    "monitoring": {
        "weight": 2,
        "keywords": (
            "prometheus",
            "grafana",
            "cloudwatch",
            "azure monitor",
            "observability",
            "monitoring",
            "incident management",
        ),
    },
    "systems": {
        "weight": 2,
        "keywords": (
            "linux",
            "windows server",
            "networking",
            "dns",
            "load balancer",
            "firewall",
            "virtual machine",
        ),
    },
}


NEGATIVE_TITLE_KEYWORDS = (
    "sales",
    "marketing",
    "recruiter",
    "human resources",
    "accountant",
    "finance manager",
    "legal counsel",
    "graphic designer",
    "content writer",
    "customer success manager",
)


REMOTE_KEYWORDS = (
    "remote",
    "fully remote",
    "work from home",
    "work-from-home",
    "distributed",
)


PREFERRED_LOCATIONS = (
    "remote",
    "pune",
    "mumbai",
    "maharashtra",
)


MINIMUM_RELEVANCE_SCORE = 8