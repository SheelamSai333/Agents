"""
SEO Rule modules and default rule registry.
"""

from typing import List
from seo_audit.rules.base import BaseRule
from seo_audit.rules.canonical import CanonicalRule
from seo_audit.rules.content import ContentRule
from seo_audit.rules.headings import HeadingsRule
from seo_audit.rules.http_status import HttpStatusRule
from seo_audit.rules.https_security import HttpsSecurityRule
from seo_audit.rules.images import ImagesRule
from seo_audit.rules.language import LanguageRule
from seo_audit.rules.links import LinksRule
from seo_audit.rules.meta_tags import MetaTagsRule
from seo_audit.rules.robots_meta import RobotsMetaRule
from seo_audit.rules.social import SocialMetadataRule
from seo_audit.rules.title import TitleRule


def get_default_rules() -> List[BaseRule]:
    """Instantiate and return the complete suite of standard SEO audit rules."""
    return [
        HttpStatusRule(),
        TitleRule(),
        MetaTagsRule(),
        RobotsMetaRule(),
        HeadingsRule(),
        ImagesRule(),
        CanonicalRule(),
        LinksRule(),
        HttpsSecurityRule(),
        SocialMetadataRule(),
        ContentRule(),
        LanguageRule(),
    ]
