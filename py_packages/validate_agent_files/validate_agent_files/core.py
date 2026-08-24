#!/usr/bin/env python3

"""Validation engines for skills, agents, and prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import yaml

from .loaders import (
    find_agent_files,
    find_prompt_files,
    find_skill_files,
    load_all_skills,
    load_custom_file,
    safe_load_frontmatter_with_body_line,
    SkillFileLoader,
)
from .paths import find_plugin_roots, resolve_paths
from .types import ValidationIssue, ValidationLevel, ValidationResult
from .validators.agents import build_known_agent_targets, validate_agent_frontmatter
from .validators.bundled_markdown import validate_bundled_markdown
from .validators.catalog_paths import validate_catalog_paths
from .validators.cross_reference import CrossReferenceValidator
from .validators.marketplace import validate_present_marketplaces, validate_required_marketplaces
from .validators.plugin_manifest import (
    find_packaged_plugin_root,
    find_plugin_root,
    PLUGIN_MANIFEST,
    validate_plugin_manifests,
)
from .validators.prompts import (
    validate_prompt_body,
    validate_prompt_frontmatter,
    validate_prompt_references,
)
from .validators.uniqueness import UniquenessValidator

# Claude Code frontmatter fields absent from the vendor-neutral Agent Skills
# Spec that skills-ref enforces. Valid here, unknown to upstream.
VENDOR_FRONTMATTER_FIELDS = frozenset({'disable-model-invocation'})

_UNEXPECTED_FIELDS_PREFIX = 'Unexpected fields in frontmatter: '


def _filter_vendor_field_error(message: str) -> str | None:
    """
    Drop upstream unknown-field errors that name only vendor fields.

    skills-ref reports every unknown field in one message. Returns None to
    discard it when all named fields are vendor ones, the message narrowed to
    the genuinely unknown remainder otherwise, and the message unchanged when
    it is a different error.
    """
    if not message.startswith(_UNEXPECTED_FIELDS_PREFIX):
        return message

    field_list = message[len(_UNEXPECTED_FIELDS_PREFIX) :].split('.', 1)[0]
    reported = {field.strip() for field in field_list.split(',') if field.strip()}
    unknown = reported - VENDOR_FRONTMATTER_FIELDS
    if not unknown:
        return None
    if unknown == reported:
        return message
    return message.replace(field_list, ', '.join(sorted(unknown)), 1)


def skills_ref_validate(skill_dir: Path | str) -> list[str]:
    """Validate a skill directory using the upstream skills-ref package."""
    from skills_ref import validate as validate_skill  # type: ignore[import-not-found]

    skill_dir = Path(skill_dir)
    messages = (_filter_vendor_field_error(m) for m in validate_skill(skill_dir))
    return [message for message in messages if message is not None]


class ValidationEngine:
    """Orchestrates validation of skills."""

    def __init__(self, show_warnings: bool = False, show_info: bool = False):
        self.show_warnings = show_warnings
        self.show_info = show_info

    def validate(self, skill_path: str, all_skills: Optional[Dict] = None) -> ValidationResult:
        all_skills = all_skills or {}
        result = ValidationResult(skill_path=skill_path, issues=[])

        try:
            frontmatter, body, body_start_line = safe_load_frontmatter_with_body_line(skill_path)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f'Failed to parse file: {exc}',
                    section='parsing',
                )
            )
            return result

        skill_dir = Path(skill_path).parent
        for message in skills_ref_validate(skill_dir):
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=message,
                    section='skills_ref',
                )
            )

        if result.issues:
            return result

        unique_validator = UniquenessValidator(all_skills=all_skills)
        result.issues.extend(
            unique_validator.validate(skill_path=skill_path, metadata=frontmatter, content=body)
        )

        # Only plugin-hosted skills are affected: outside a plugin the literal
        # path still resolves, so flagging it would be a false positive. Either
        # ecosystem's manifest marks a plugin, since both ship to a cache.
        plugin_root = find_packaged_plugin_root(skill_path)

        xref_validator = CrossReferenceValidator(
            base_path=str(skill_dir),
            show_warnings=self.show_warnings,
            plugin_root=None if plugin_root is None else str(plugin_root),
        )
        result.issues.extend(
            xref_validator.validate(
                skill_path=skill_path,
                metadata=frontmatter,
                content=body,
                line_offset=body_start_line - 1,
            )
        )

        if plugin_root is not None:
            result.issues.extend(validate_catalog_paths(body, line_offset=body_start_line - 1))

        return result


class CustomizationsValidationEngine:
    """Orchestrates validation for skills, agents, and prompts."""

    def __init__(
        self,
        show_warnings: bool = False,
        require_marketplaces: Sequence[str] = (),
        mode: str = 'files',
    ):
        self.show_warnings = show_warnings
        self.require_marketplaces = require_marketplaces
        self.mode = mode

    @property
    def plugin_mode(self) -> bool:
        """Whether packaging is validated: asked for, or implied by a requirement."""
        return self.mode == 'plugin' or bool(self.require_marketplaces)

    def validate(self, path: str, kind: str) -> List[ValidationResult]:
        """Validate one customization path."""
        return self.validate_paths([path], kind)

    def validate_paths(self, requested_paths: List[str], kind: str) -> List[ValidationResult]:
        """Validate customization paths as one shared catalog."""
        paths, results = resolve_paths(requested_paths)
        results.extend(validate_required_marketplaces(self.require_marketplaces))
        if self.plugin_mode:
            results.extend(validate_present_marketplaces(skip=self.require_marketplaces))
        results.extend(self._report_empty_paths(paths))
        results.extend(self._validate_plugin_manifests(paths))
        results.extend(self._validate_bundled_markdown(paths))

        if kind in {'all', 'skills'}:
            skill_files = self._unique_files(
                file_path
                for path in paths
                for file_path in SkillFileLoader().find_skill_files(path)
            )
            results.extend(self._validate_skill_files(skill_files))
        if kind in {'all', 'agents'}:
            agent_files = self._unique_files(
                file_path for path in paths for file_path in find_agent_files(path)
            )
            results.extend(self._validate_agent_files(agent_files))
        if kind in {'all', 'prompts'}:
            prompt_files = self._unique_files(
                file_path for path in paths for file_path in find_prompt_files(path)
            )
            results.extend(self._validate_prompt_files(prompt_files))

        return results

    @staticmethod
    def _report_empty_paths(paths: List[str]) -> List[ValidationResult]:
        """
        Report every requested path that holds nothing this tool can validate.

        A path that yields no files validates nothing, and a run that validates
        nothing is indistinguishable from a clean one. Discovery ignores the
        requested ``kind`` on purpose: asking a skills-only catalog for its
        agents is an empty answer by request, not a broken path.
        """
        results = []
        for path in paths:
            if find_skill_files(path) or find_agent_files(path) or find_prompt_files(path):
                continue
            results.append(
                ValidationResult(
                    skill_path=path,
                    issues=[
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f'{path} contains no skills, agents, or prompts',
                            section='paths',
                        )
                    ],
                )
            )
        return results

    def _validate_plugin_manifests(self, paths: List[str]) -> List[ValidationResult]:
        """
        Validate the manifests of every plugin this run covers.

        A requested path inside a plugin always carries its plugin with it, so
        those manifests are checked in every mode. Plugin mode adds the plugins
        the marketplace manifests publish, which is how a repository root — above
        its plugins rather than inside one — gets its packaging validated.
        Discovery errors, and a published plugin that ships no Claude manifest at
        all, are left to the marketplace validators, which report them once.
        """
        plugin_roots = [
            plugin_root for path in paths if (plugin_root := find_plugin_root(path)) is not None
        ]
        if self.plugin_mode:
            published, _errors = find_plugin_roots(Path.cwd())
            plugin_roots.extend(
                Path(candidate)
                for candidate in published
                if (Path(candidate) / PLUGIN_MANIFEST).is_file()
            )

        unique_roots = dict.fromkeys(plugin_root.resolve() for plugin_root in plugin_roots)
        return [validate_plugin_manifests(plugin_root) for plugin_root in unique_roots]

    def _validate_bundled_markdown(self, paths: List[str]) -> List[ValidationResult]:
        """
        Check the references of markdown a plugin ships outside its catalog entries.

        Catalog discovery finds only ``SKILL.md``, ``*.agent.md``, and
        ``*.prompt.md``, so a ``references/`` page or a plugin ``README.md``
        could carry a reference out of the plugin unnoticed. Roots come from the
        requested paths, plus the published plugins in plugin mode, and either
        ecosystem's manifest marks one.
        """
        plugin_roots = [
            plugin_root
            for path in paths
            if (plugin_root := find_packaged_plugin_root(path)) is not None
        ]
        if self.plugin_mode:
            published, _errors = find_plugin_roots(Path.cwd())
            plugin_roots.extend(Path(candidate) for candidate in published)

        unique_roots = dict.fromkeys(plugin_root.resolve() for plugin_root in plugin_roots)
        return [
            result
            for plugin_root in unique_roots
            for result in validate_bundled_markdown(plugin_root)
        ]

    @staticmethod
    def _unique_files(file_paths: Iterable[str]) -> List[str]:
        """Return discovered files once while preserving discovery order."""
        return list(dict.fromkeys(file_paths))

    def _validate_skill_files(self, skill_files: List[str]) -> List[ValidationResult]:
        all_skills = load_all_skills(skill_files)
        engine = ValidationEngine(show_warnings=self.show_warnings)
        return [engine.validate(skill_path, all_skills=all_skills) for skill_path in skill_files]

    def _validate_skills(self, path: str) -> List[ValidationResult]:
        return self._validate_skill_files(SkillFileLoader().find_skill_files(path))

    def _validate_agents(self, path: str) -> List[ValidationResult]:
        return self._validate_agent_files(find_agent_files(path))

    def _validate_agent_files(self, agent_files: List[str]) -> List[ValidationResult]:
        agent_documents: Dict[str, dict] = {}
        parse_errors: Dict[str, ValidationResult] = {}

        for file_path in agent_files:
            try:
                document = load_custom_file(file_path)
            except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
                parse_errors[file_path] = ValidationResult(
                    skill_path=file_path,
                    issues=[
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f'Failed to parse file: {exc}',
                            section='parsing',
                        )
                    ],
                )
                continue

            if document.has_frontmatter:
                frontmatter = document.frontmatter
                frontmatter['_identifier'] = Path(file_path).name.removesuffix('.agent.md')
                agent_documents[file_path] = frontmatter

        known_targets = build_known_agent_targets(agent_documents)
        results: List[ValidationResult] = []
        for file_path in agent_files:
            if file_path in parse_errors:
                results.append(parse_errors[file_path])
                continue

            result = self._validate_agent_file(file_path, known_targets)
            results.append(result)

        return results

    def _validate_agent_file(self, file_path: str, known_targets: set[str]) -> ValidationResult:
        result = ValidationResult(skill_path=file_path, issues=[])
        document = load_custom_file(file_path)

        if not document.has_frontmatter:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message='File must start with YAML frontmatter',
                    section='parsing',
                )
            )
            return result

        result.issues.extend(validate_agent_frontmatter(document.frontmatter, known_targets))
        agent_plugin_root = find_packaged_plugin_root(file_path)
        xref_validator = CrossReferenceValidator(
            base_path=str(Path(file_path).parent),
            plugin_root=None if agent_plugin_root is None else str(agent_plugin_root),
        )
        result.issues.extend(
            xref_validator.validate(
                skill_path=file_path,
                metadata=document.frontmatter,
                content=document.body,
                line_offset=document.body_start_line - 1,
            )
        )
        return result

    def _validate_prompt_files(self, prompt_files: List[str]) -> List[ValidationResult]:
        return [self._validate_prompt_file(file_path) for file_path in prompt_files]

    def _validate_prompts(self, path: str) -> List[ValidationResult]:
        return self._validate_prompt_files(find_prompt_files(path))

    def _validate_prompt_file(self, file_path: str) -> ValidationResult:
        result = ValidationResult(skill_path=file_path, issues=[])

        try:
            document = load_custom_file(file_path)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f'Failed to parse file: {exc}',
                    section='parsing',
                )
            )
            return result

        if not document.has_frontmatter:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message='File must start with YAML frontmatter',
                    section='parsing',
                )
            )
            return result

        result.issues.extend(validate_prompt_frontmatter(document.frontmatter))
        result.issues.extend(validate_prompt_body(document.body))

        prompt_plugin_root = find_packaged_plugin_root(file_path)
        xref_validator = CrossReferenceValidator(
            base_path=str(Path(file_path).parent),
            plugin_root=None if prompt_plugin_root is None else str(prompt_plugin_root),
        )
        result.issues.extend(
            xref_validator.validate(
                skill_path=file_path,
                metadata=document.frontmatter,
                content=document.body,
                line_offset=document.body_start_line - 1,
            )
        )
        result.issues.extend(
            validate_prompt_references(
                file_path=file_path,
                body=document.body,
                line_offset=document.body_start_line - 1,
            )
        )
        return result


__all__ = [
    'CustomizationsValidationEngine',
    'ValidationEngine',
    'ValidationIssue',
    'ValidationLevel',
    'ValidationResult',
    'skills_ref_validate',
]
