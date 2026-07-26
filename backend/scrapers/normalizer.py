"""
Metadata Normalizer Module
Converts ParsedDocument into NormalizedDocument containing clean NormalizedMetadata,
confidence-weighted field resolution, and per-field provenance tracking.
"""

from typing import Any, Dict, List, Optional, Tuple
from scrapers.models import ParsedDocument, NormalizedDocument, NormalizedMetadata
from core.logging_config import get_logger

logger = get_logger(__name__)


class MetadataNormalizer:
    """
    Normalizes metadata extracted from various plugins into a unified, provider-agnostic NormalizedDocument
    with confidence-weighted field resolution and per-field provenance tracking.
    """
    def normalize(self, parsed_doc: ParsedDocument) -> NormalizedDocument:
        field_candidates: Dict[str, List[Tuple[Any, float, str]]] = {
            "title": [],
            "description": [],
            "image_url": [],
            "author": [],
            "publisher": [],
            "canonical_url": []
        }

        og_data: Dict[str, str] = {}
        twitter_data: Dict[str, str] = {}
        schemas: List[Dict[str, Any]] = []
        image_data: Dict[str, Any] = {}
        table_code_data: Dict[str, Any] = {}

        for res in parsed_doc.plugin_results:
            if not res.success:
                continue

            conf = res.confidence
            source = res.plugin_name

            if res.plugin_name == "opengraph":
                og_data = res.extracted_data.get("open_graph", {})
                twitter_data = res.extracted_data.get("twitter_card", {})

                if og_data.get("title"):
                    field_candidates["title"].append((og_data["title"], conf, "open_graph"))
                elif twitter_data.get("title"):
                    field_candidates["title"].append((twitter_data["title"], conf * 0.9, "twitter_card"))

                if og_data.get("description"):
                    field_candidates["description"].append((og_data["description"], conf, "open_graph"))
                elif twitter_data.get("description"):
                    field_candidates["description"].append((twitter_data["description"], conf * 0.9, "twitter_card"))

                if og_data.get("image"):
                    field_candidates["image_url"].append((og_data["image"], conf, "open_graph"))
                elif twitter_data.get("image"):
                    field_candidates["image_url"].append((twitter_data["image"], conf * 0.9, "twitter_card"))

                if og_data.get("article:author"):
                    field_candidates["author"].append((og_data["article:author"], conf, "open_graph"))
                if og_data.get("site_name"):
                    field_candidates["publisher"].append((og_data["site_name"], conf, "open_graph"))
                if og_data.get("url"):
                    field_candidates["canonical_url"].append((og_data["url"], conf, "open_graph"))

            elif res.plugin_name == "json_ld":
                schemas = res.extracted_data.get("schema_org", [])
                headline = self._find_schema_val(schemas, "headline") or self._find_schema_val(schemas, "name")
                if headline:
                    field_candidates["title"].append((headline, conf, "json_ld"))

                desc = self._find_schema_val(schemas, "description")
                if desc:
                    field_candidates["description"].append((desc, conf, "json_ld"))

                author_schema = self._find_author(schemas)
                if author_schema:
                    field_candidates["author"].append((author_schema, conf, "json_ld"))

                pub_schema = self._find_publisher(schemas)
                if pub_schema:
                    field_candidates["publisher"].append((pub_schema, conf, "json_ld"))

            elif res.plugin_name == "readability":
                raw_t = res.extracted_data.get("title")
                if raw_t:
                    field_candidates["title"].append((raw_t, conf, "readability"))

            elif res.plugin_name == "image":
                image_data = res.extracted_data
                main_img = image_data.get("main_image_url")
                if main_img:
                    field_candidates["image_url"].append((main_img, conf, "image_plugin"))

            elif res.plugin_name == "table_code":
                table_code_data = res.extracted_data

        # Fallback for raw title
        if parsed_doc.raw_title:
            field_candidates["title"].append((parsed_doc.raw_title, 0.5, "parsed_html"))

        # Resolve best values by confidence
        field_provenance: Dict[str, str] = {}
        field_confidence: Dict[str, float] = {}
        resolved_fields: Dict[str, Any] = {}

        for field_name, candidates in field_candidates.items():
            if candidates:
                # Sort candidates by confidence descending
                candidates.sort(key=lambda x: x[1], reverse=True)
                val, confidence, source = candidates[0]
                resolved_fields[field_name] = val.strip() if isinstance(val, str) else val
                field_provenance[field_name] = source
                field_confidence[field_name] = confidence
            else:
                resolved_fields[field_name] = None

        # Title fallback
        title = resolved_fields["title"] or "Untitled Bookmark"
        if "title" not in field_provenance:
            field_provenance["title"] = "default_fallback"
            field_confidence["title"] = 0.1

        canonical_url = resolved_fields["canonical_url"] or parsed_doc.url
        if "canonical_url" not in field_provenance:
            field_provenance["canonical_url"] = "input_url"
            field_confidence["canonical_url"] = 1.0

        # Calculate Reading Time
        words = parsed_doc.clean_text.split() if parsed_doc.clean_text else []
        reading_time_minutes = max(1, len(words) // 200) if words else 0
        field_provenance["reading_time"] = "readability"
        field_confidence["reading_time"] = 0.9

        norm_metadata = NormalizedMetadata(
            title=title,
            description=resolved_fields["description"],
            image_url=resolved_fields["image_url"],
            author=resolved_fields["author"],
            publisher=resolved_fields["publisher"],
            canonical_url=canonical_url,
            reading_time_minutes=reading_time_minutes,
            field_provenance=field_provenance,
            field_confidence=field_confidence
        )

        provider_raw_payload = {
            "open_graph": og_data,
            "twitter_card": twitter_data,
            "schema_org": schemas,
            "images": image_data.get("images", []),
            "code_blocks": table_code_data.get("code_blocks", []),
            "tables": table_code_data.get("tables", [])
        }

        return NormalizedDocument(
            url=parsed_doc.url,
            canonical_url=canonical_url,
            markdown_content=parsed_doc.markdown_body,
            metadata=norm_metadata,
            provider_raw_payload=provider_raw_payload,
            fetch_metadata=parsed_doc.fetch_metadata
        )

    def _find_schema_val(self, schemas: List[Dict[str, Any]], key: str) -> Optional[str]:
        for s in schemas:
            if key in s and isinstance(s[key], str):
                return s[key]
        return None

    def _find_author(self, schemas: List[Dict[str, Any]]) -> Optional[str]:
        for s in schemas:
            author_val = s.get("author")
            if isinstance(author_val, str):
                return author_val
            elif isinstance(author_val, dict) and "name" in author_val:
                return str(author_val["name"])
            elif isinstance(author_val, list) and len(author_val) > 0:
                first = author_val[0]
                if isinstance(first, str):
                    return first
                elif isinstance(first, dict) and "name" in first:
                    return str(first["name"])
        return None

    def _find_publisher(self, schemas: List[Dict[str, Any]]) -> Optional[str]:
        for s in schemas:
            pub_val = s.get("publisher")
            if isinstance(pub_val, str):
                return pub_val
            elif isinstance(pub_val, dict) and "name" in pub_val:
                return str(pub_val["name"])
        return None
