"""
Rules used by Job Relevance Filtering v0.2.

Explicit role titles qualify directly.

Generic or ambiguous role titles qualify only when their job title,
description, or other searchable fields contain sufficient supporting
technology evidence.
"""


TARGET_ROLE_GROUPS = {
    "devops": {
        "weight": 10,
        "keywords": (
            "devops engineer",
            "devops",
            "ci/cd engineer",
            "continuous integration engineer",
            "continuous deployment engineer",
        ),
    },
    "sre": {
        "weight": 10,
        "keywords": (
            "site reliability engineer",
            "site reliability",
            "sre engineer",
            "sre",
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
            "azure technical support engineer",
            "aws technical support engineer",
            "microsoft 365 support engineer",
            "office 365 support engineer",
            "m365 support engineer",
        ),
    },
    "platform_engineering": {
        "weight": 8,
        "keywords": (
            "platform operations engineer",
            "cloud platform engineer",
        ),
    },
    "production_support": {
        "weight": 6,
        "keywords": (
            "production support engineer",
        ),
    },
}


CONDITIONAL_ROLE_RULES = {
    "sre": (
        {
            "keywords": (
                "reliability engineer",
            ),
            "required_all_technology_groups": (
                "monitoring",
            ),
            "required_any_technology_groups": (
                "cloud",
                "devops_tools",
                "containers",
                "systems",
            ),
            "minimum_technology_groups": 2,
        },
    ),
    "cloud_operations": (
        {
            "keywords": (
                "infrastructure engineer",
                "systems administrator",
                "system administrator",
                "infrastructure administrator",
            ),
            "required_all_technology_groups": (),
            "required_any_technology_groups": (
                "cloud",
                "devops_tools",
                "containers",
            ),
            "minimum_technology_groups": 2,
        },
    ),
    "cloud_support": (
        {
            "keywords": (
                "technical support engineer",
            ),
            "required_all_technology_groups": (
                "cloud",
            ),
            "required_any_technology_groups": (),
            "minimum_technology_groups": 1,
        },
    ),
    "platform_engineering": (
        {
            "keywords": (
                "platform engineer",
            ),
            "required_all_technology_groups": (),
            "required_any_technology_groups": (
                "cloud",
                "devops_tools",
                "containers",
            ),
            "minimum_technology_groups": 1,
        },
        {
            "keywords": (
                "production engineer",
            ),
            "required_all_technology_groups": (),
            "required_any_technology_groups": (
                "cloud",
                "devops_tools",
                "containers",
                "monitoring",
                "systems",
            ),
            "minimum_technology_groups": 2,
        },
    ),
    "production_support": (
        {
            "keywords": (
                "application support engineer",
                "technical operations engineer",
                "operations support engineer",
                "l2 support engineer",
                "l3 support engineer",
            ),
            "required_all_technology_groups": (),
            "required_any_technology_groups": (
                "cloud",
                "devops_tools",
                "containers",
                "monitoring",
                "systems",
            ),
            "minimum_technology_groups": 1,
        },
    ),
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
            "m365",
            "google cloud platform",
            "gcp",
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
            "continuous integration",
            "continuous deployment",
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
            "containers",
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
            "application monitoring",
            "infrastructure monitoring",
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
            "virtual machines",
            "active directory",
            "entra id",
            "rbac",
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
    "intern",
    "internship",
    "audiovisual",
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