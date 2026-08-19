from __future__ import annotations

from dataclasses import dataclass, field

from app.policies import youtube_metadata_v1 as rules
from app.services.export_service import PublishingPackage


@dataclass
class MetadataValidationReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class YouTubeMetadataValidator:
    def validate(self, package: PublishingPackage) -> MetadataValidationReport:
        errors: list[str] = []
        warnings: list[str] = []

        title = package.title.strip()
        if not title:
            errors.append("Title is required.")
        elif len(title) > rules.TITLE_MAX_LENGTH:
            errors.append(f"Title exceeds {rules.TITLE_MAX_LENGTH} characters.")
        elif len(title) > rules.TITLE_RECOMMENDED_MAX:
            warnings.append(f"Title exceeds recommended {rules.TITLE_RECOMMENDED_MAX} characters for Shorts.")

        description = package.description.strip()
        if not description:
            errors.append("Description is required.")
        elif len(description) > rules.DESCRIPTION_MAX_LENGTH:
            errors.append(f"Description exceeds {rules.DESCRIPTION_MAX_LENGTH} characters.")

        if len(package.hashtags) > rules.HASHTAG_MAX_COUNT:
            errors.append(f"Hashtag count exceeds {rules.HASHTAG_MAX_COUNT}.")
        for tag in package.hashtags:
            if not tag.startswith("#"):
                errors.append(f"Hashtag must start with '#': {tag}")
            elif " " in tag:
                errors.append(f"Hashtag must not contain spaces: {tag}")
            elif len(tag) > rules.HASHTAG_MAX_LENGTH + 1:
                errors.append(f"Hashtag too long: {tag}")

        pinned = package.pinned_comment.strip()
        if pinned and len(pinned) > rules.PINNED_COMMENT_MAX_LENGTH:
            errors.append(f"Pinned comment exceeds {rules.PINNED_COMMENT_MAX_LENGTH} characters.")

        combined = f"{title} {description} {' '.join(package.hashtags)} {pinned}".lower()
        for word in rules.RESTRICTED_WORDS:
            if word in combined:
                errors.append(f"Metadata contains restricted phrase: {word}")

        if rules.REQUIRED_DISCLOSURE and rules.REQUIRED_DISCLOSURE.lower() not in description.lower():
            errors.append(f"Description must include required disclosure: {rules.REQUIRED_DISCLOSURE}")

        return MetadataValidationReport(valid=not errors, errors=errors, warnings=warnings)
