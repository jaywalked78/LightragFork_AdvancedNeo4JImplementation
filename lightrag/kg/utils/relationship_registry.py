"""
Relationship registry for Neo4j graph storage.
This module provides a registry for all supported relationship types for tech/development domains.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from difflib import SequenceMatcher

from fuzzywuzzy import fuzz

from ...utils import logger


def standardize_relationship_type(rel_type: str) -> str:
    """
    Convert a relationship type string to Neo4j standard format.
    
    Args:
        rel_type: Original relationship type string (e.g., "integrates with", "calls api")
        
    Returns:
        Standardized relationship type (e.g., "INTEGRATES_WITH", "CALLS_API")
    """
    if not rel_type:
        return "RELATED"
    
    # Remove special characters, replace spaces with underscores, uppercase
    std_type = re.sub(r'[^a-zA-Z0-9\s]', '', rel_type)
    std_type = re.sub(r'\s+', '_', std_type)
    
    # Ensure it's uppercase and not empty
    result = std_type.upper() if std_type else "RELATED"
    
    # Truncate if too long for Neo4j (which has a limit for identifier length)
    if len(result) > 50:
        result = result[:50]
        
    return result


class RelationshipTypeRegistry:
    """Registry of valid relationship types with their metadata for tech/development domain."""
    
    def __init__(self):
        """Initialize with the supported relationship types."""
        self.registry = {}
        self._initialize_registry()
    
    def _initialize_registry(self):
        """Initialize with tech/development focused relationship types."""
        # Tech/Development focused relationship types
        relationship_types = [
            # AI/ML Relationships
            "TRAINS_MODEL",
            "USES_EMBEDDINGS",
            "GENERATES_RESPONSE",
            "QUERIES_LLM",
            "FINE_TUNES",
            "PROMPTS",
            "VECTORIZES",
            "SEMANTIC_SEARCH",
            "AUGMENTS_DATA",
            
            # API & Integration
            "CALLS_API",
            "EXPOSES_ENDPOINT",
            "INTEGRATES_WITH",
            "WEBHOOKS_TO",
            "SUBSCRIBES_TO",
            "PUBLISHES_TO",
            "AUTHENTICATES_WITH",
            "RATE_LIMITS",
            "PROXIES_TO",
            
            # Frontend Development
            "RENDERS_COMPONENT",
            "MANAGES_STATE",
            "ROUTES_TO",
            "DISPLAYS_DATA",
            "HANDLES_EVENT",
            "STYLES_WITH",
            "ANIMATES",
            "RESPONSIVE_TO",
            "LAZY_LOADS",
            
            # Backend Development
            "PROCESSES_REQUEST",
            "QUERIES_DATABASE",
            "CACHES_IN",
            "VALIDATES_DATA",
            "TRANSFORMS_DATA",
            "SCHEDULES_JOB",
            "QUEUES_TASK",
            "LOGS_TO",
            "MONITORS",
            
            # Data Flow
            "READS_FROM",
            "WRITES_TO",
            "STREAMS_DATA",
            "BATCHES_DATA",
            "AGGREGATES",
            "FILTERS",
            "MAPS_TO",
            "REDUCES_TO",
            "PIPELINES_THROUGH",
            
            # Architecture & Infrastructure
            "DEPLOYS_TO",
            "CONTAINERIZED_IN",
            "ORCHESTRATES",
            "LOAD_BALANCES",
            "SCALES_WITH",
            "HOSTED_ON",
            "BACKED_BY",
            "REPLICATES_TO",
            "FAILOVER_TO",
            
            # Development Process
            "DEPENDS_ON",
            "EXTENDS",
            "IMPLEMENTS",
            "INHERITS_FROM",
            "COMPOSES",
            "DECORATES",
            "MOCKS",
            "TESTS",
            "DEBUGS",
            
            # Automation
            "AUTOMATES",
            "TRIGGERS",
            "SCHEDULES",
            "ORCHESTRATES_WORKFLOW",
            "CHAINS_TO",
            "BRANCHES_TO",
            "RETRIES_ON",
            "ROLLBACK_TO",
            "NOTIFIES",
            
            # Security & Auth
            "AUTHORIZES",
            "ENCRYPTS",
            "SIGNS_WITH",
            "VALIDATES_TOKEN",
            "GRANTS_ACCESS",
            "REVOKES_ACCESS",
            "AUDITS",
            "SECURES",
            
            # Version Control & CI/CD
            "COMMITS_TO",
            "MERGES_INTO",
            "BRANCHES_FROM",
            "TAGS_AS",
            "BUILDS_FROM",
            "PACKAGES_AS",
            "RELEASES_TO",
            "ROLLBACKS_FROM",
            
            # Documentation & Knowledge
            "DOCUMENTS",
            "REFERENCES",
            "ANNOTATES",
            "EXAMPLES_OF",
            "TUTORIALS_FOR",
            "MIGRATES_FROM",
            "DEPRECATED_BY",
            "REPLACES",
            
            # Performance & Optimization
            "OPTIMIZES",
            "INDEXES",
            "COMPRESSES",
            "MINIFIES",
            "BUNDLES_WITH",
            "LAZY_EVALUATES",
            "MEMOIZES",
            "PARALLELIZES",
            
            # Generic
            "RELATED",
            "CONNECTED_TO",
            "ASSOCIATED_WITH",
            "PART_OF",
            "CONTAINS",
            "BELONGS_TO"
        ]

        # Common relationship variants that need normalization
        common_variants = {
            # AI/ML variants
            "uses ai": "USES_EMBEDDINGS",
            "ai powered": "USES_EMBEDDINGS",
            "machine learning": "TRAINS_MODEL",
            "calls gpt": "QUERIES_LLM",
            "uses llm": "QUERIES_LLM",
            "generates with ai": "GENERATES_RESPONSE",
            
            # API variants
            "api call": "CALLS_API",
            "makes request to": "CALLS_API",
            "posts to": "CALLS_API",
            "gets from": "CALLS_API",
            "fetches from": "CALLS_API",
            "sends webhook": "WEBHOOKS_TO",
            "listens to": "SUBSCRIBES_TO",
            "broadcasts to": "PUBLISHES_TO",
            
            # Frontend variants
            "displays": "DISPLAYS_DATA",
            "shows": "DISPLAYS_DATA",
            "renders": "RENDERS_COMPONENT",
            "handles click": "HANDLES_EVENT",
            "on click": "HANDLES_EVENT",
            "styled with": "STYLES_WITH",
            "uses css": "STYLES_WITH",
            "navigates to": "ROUTES_TO",
            
            # Backend variants
            "processes": "PROCESSES_REQUEST",
            "handles request": "PROCESSES_REQUEST",
            "queries": "QUERIES_DATABASE",
            "selects from": "QUERIES_DATABASE",
            "inserts into": "WRITES_TO",
            "updates": "WRITES_TO",
            "deletes from": "WRITES_TO",
            "caches": "CACHES_IN",
            
            # Data flow variants
            "reads": "READS_FROM",
            "writes": "WRITES_TO",
            "saves to": "WRITES_TO",
            "loads from": "READS_FROM",
            "imports from": "READS_FROM",
            "exports to": "WRITES_TO",
            "transforms": "TRANSFORMS_DATA",
            "converts": "TRANSFORMS_DATA",
            
            # Architecture variants
            "deployed on": "DEPLOYS_TO",
            "runs on": "HOSTED_ON",
            "hosted by": "HOSTED_ON",
            "uses database": "BACKED_BY",
            "backed by": "BACKED_BY",
            "dockerized": "CONTAINERIZED_IN",
            "in container": "CONTAINERIZED_IN",
            
            # Development variants
            "requires": "DEPENDS_ON",
            "needs": "DEPENDS_ON",
            "uses": "DEPENDS_ON",
            "based on": "EXTENDS",
            "built on": "EXTENDS",
            "implements interface": "IMPLEMENTS",
            "tested by": "TESTS",
            "unit test": "TESTS",
            
            # Automation variants
            "automated by": "AUTOMATES",
            "triggers when": "TRIGGERS",
            "runs after": "CHAINS_TO",
            "follows": "CHAINS_TO",
            "notifies via": "NOTIFIES",
            "alerts": "NOTIFIES",
            
            # Generic variants
            "related to": "RELATED",
            "is related to": "RELATED",
            "connected with": "CONNECTED_TO",
            "is part of": "PART_OF",
            "includes": "CONTAINS",
            "has": "CONTAINS"
        }

        # Populate the registry with Neo4j types and additional metadata
        for rel_type in relationship_types:
            # Convert to lowercase for registry keys
            original_type = rel_type.lower().replace('_', ' ')
            
            # Add to registry with metadata
            self.registry[original_type] = {
                "neo4j_type": rel_type,
                "description": f"Relationship type: {original_type}",
                "bidirectional": original_type in ["related", "connected to", "associated with"],
                "inverse": None
            }
        
        # Add common variants
        for variant, standard in common_variants.items():
            if variant not in self.registry:
                # Find the standardized form in our registry
                standard_key = standard.lower().replace('_', ' ')
                if standard_key in self.registry:
                    # Use the same metadata but with the variant's neo4j_type
                    self.registry[variant] = {
                        "neo4j_type": standard,
                        "description": f"Variant of {standard_key}: {variant}",
                        "bidirectional": self.registry[standard_key].get("bidirectional", False),
                        "inverse": self.registry[standard_key].get("inverse", None)
                    }
        
        # Define explicit bidirectional relationships and inverses
        inverse_pairs = [
            # API/Integration
            ("calls api", "exposes endpoint"),
            ("subscribes to", "publishes to"),
            ("webhooks to", "receives webhook from"),
            
            # Data flow
            ("reads from", "read by"),
            ("writes to", "written by"),
            ("streams data", "receives stream"),
            
            # Architecture
            ("deploys to", "hosts"),
            ("depends on", "required by"),
            ("extends", "extended by"),
            ("implements", "implemented by"),
            
            # Frontend/Backend
            ("renders component", "rendered by"),
            ("displays data", "displayed by"),
            ("processes request", "processed by"),
            ("queries database", "queried by"),
            
            # Automation
            ("triggers", "triggered by"),
            ("automates", "automated by"),
            ("chains to", "chained from"),
            
            # Development
            ("tests", "tested by"),
            ("documents", "documented by"),
            ("replaces", "replaced by"),
            ("migrates from", "migrates to"),
            
            # Structure
            ("contains", "part of"),
            ("composes", "composed by"),
            ("inherits from", "inherited by")
        ]
        
        # Set up the inverse relationships
        for rel1, rel2 in inverse_pairs:
            if rel1 in self.registry and rel2 in self.registry:
                self.registry[rel1]["inverse"] = rel2
                self.registry[rel2]["inverse"] = rel1
        
        logger.info(f"Initialized tech/development relationship registry with {len(self.registry)} types")
    
    def get_neo4j_type(self, original_type: str) -> str:
        """
        Get standardized Neo4j type from original relationship description.
        
        Args:
            original_type: Original relationship type string
            
        Returns:
            Neo4j-compatible relationship type string
        """
        if not original_type:
            return "RELATED"
        
        # Convert to lowercase for case-insensitive lookup
        original_type_lower = original_type.lower()
        
        # Direct lookup
        if original_type_lower in self.registry:
            return self.registry[original_type_lower]["neo4j_type"]
        
        # Find closest match
        closest_match = self._find_closest_match(original_type_lower)
        if closest_match:
            return self.registry[closest_match]["neo4j_type"]
        
        # If no match found, standardize the original
        return standardize_relationship_type(original_type)
    
    def get_relationship_metadata(self, original_type: str) -> Dict[str, Any]:
        """
        Get metadata for a relationship type.
        
        Args:
            original_type: Original relationship type string
            
        Returns:
            Dictionary of metadata for the relationship type
        """
        original_type_lower = original_type.lower()
        
        # Direct lookup
        if original_type_lower in self.registry:
            return self.registry[original_type_lower]
        
        # Find closest match
        closest_match = self._find_closest_match(original_type_lower)
        if closest_match:
            return self.registry[closest_match]
        
        # If no match found, return default metadata
        neo4j_type = standardize_relationship_type(original_type)
        return {
            "neo4j_type": neo4j_type,
            "description": f"Custom relationship type: {original_type}",
            "bidirectional": False,
            "inverse": None
        }
    
    def get_all_relationship_types(self) -> List[str]:
        """
        Get all registered relationship types.
        
        Returns:
            List of all registered relationship types
        """
        return list(self.registry.keys())
    
    def get_bidirectional_types(self) -> List[str]:
        """
        Get all bidirectional relationship types.
        
        Returns:
            List of bidirectional relationship types
        """
        return [
            rel for rel, metadata in self.registry.items()
            if metadata.get("bidirectional", False)
        ]
    
    def get_relationship_pairs(self) -> List[Tuple[str, str]]:
        """
        Get all relationship types with their inverses.
        
        Returns:
            List of (relationship_type, inverse_type) tuples
        """
        return [
            (rel, metadata["inverse"])
            for rel, metadata in self.registry.items()
            if metadata.get("inverse") is not None
        ]
    
    def _find_closest_match(self, rel_type: str) -> Optional[str]:
        """
        Find the closest matching registered relationship type.
        
        This method uses fuzzy matching to find similar relationship types,
        which is crucial for handling LLM-generated variations.
        
        Args:
            rel_type: Relationship type to find match for
            
        Returns:
            The closest matching relationship type or None if no good match found
        """
        if not rel_type:
            return None
        
        # Check for substring matches first (more precise)
        for reg_type in self.registry:
            # Check if one is a substring of the other
            if rel_type in reg_type or reg_type in rel_type:
                return reg_type
        
        # If no substring match, use fuzzy matching
        best_match = None
        best_score = 70  # Minimum similarity threshold (0-100)
        
        for reg_type in self.registry:
            # Calculate similarity score (0-100)
            score = fuzz.ratio(rel_type, reg_type)
            if score > best_score:
                best_score = score
                best_match = reg_type
                
        return best_match

    def validate_relationship_type(self, rel_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a relationship type is registered or similar to a registered type.
        
        Args:
            rel_type: Relationship type to validate
            
        Returns:
            (is_valid, suggested_alternative) tuple
        """
        if not rel_type:
            return False, "related"
        
        rel_type_lower = rel_type.lower()
        
        # Direct match
        if rel_type_lower in self.registry:
            return True, None
        
        # Find closest match
        closest_match = self._find_closest_match(rel_type_lower)
        if closest_match:
            return False, closest_match
        
        return False, None

    def get_category_relationships(self, category: str) -> List[str]:
        """
        Get all relationships belonging to a specific category.
        
        Categories: ai_ml, api, frontend, backend, data, architecture, 
                   development, automation, security, vcs, docs, performance
        
        Args:
            category: Category name
            
        Returns:
            List of relationship types in that category
        """
        categories = {
            "ai_ml": [
                "trains model", "uses embeddings", "generates response", 
                "queries llm", "fine tunes", "prompts", "vectorizes", 
                "semantic search", "augments data"
            ],
            "api": [
                "calls api", "exposes endpoint", "integrates with", 
                "webhooks to", "subscribes to", "publishes to", 
                "authenticates with", "rate limits", "proxies to"
            ],
            "frontend": [
                "renders component", "manages state", "routes to", 
                "displays data", "handles event", "styles with", 
                "animates", "responsive to", "lazy loads"
            ],
            "backend": [
                "processes request", "queries database", "caches in", 
                "validates data", "transforms data", "schedules job", 
                "queues task", "logs to", "monitors"
            ],
            "data": [
                "reads from", "writes to", "streams data", "batches data", 
                "aggregates", "filters", "maps to", "reduces to", 
                "pipelines through"
            ],
            "architecture": [
                "deploys to", "containerized in", "orchestrates", 
                "load balances", "scales with", "hosted on", "backed by", 
                "replicates to", "failover to"
            ],
            "development": [
                "depends on", "extends", "implements", "inherits from", 
                "composes", "decorates", "mocks", "tests", "debugs"
            ],
            "automation": [
                "automates", "triggers", "schedules", "orchestrates workflow", 
                "chains to", "branches to", "retries on", "rollback to", 
                "notifies"
            ],
            "security": [
                "authorizes", "encrypts", "signs with", "validates token", 
                "grants access", "revokes access", "audits", "secures"
            ],
            "vcs": [
                "commits to", "merges into", "branches from", "tags as", 
                "builds from", "packages as", "releases to", "rollbacks from"
            ],
            "docs": [
                "documents", "references", "annotates", "examples of", 
                "tutorials for", "migrates from", "deprecated by", "replaces"
            ],
            "performance": [
                "optimizes", "indexes", "compresses", "minifies", 
                "bundles with", "lazy evaluates", "memoizes", "parallelizes"
            ]
        }
        
        return categories.get(category.lower(), [])