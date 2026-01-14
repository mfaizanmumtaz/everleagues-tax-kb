"""Jurisdictions Configuration Loader.

This module loads and provides access to valid states, cities, categories,
and other jurisdiction-related configuration values.

Usage:
    from app.config.jurisdiction_config import (
        get_valid_states,
        get_valid_cities,
        is_valid_state,
        is_valid_city,
    )
    
    # Get all valid state codes
    states = get_valid_states()  # ['AL', 'AK', 'AZ', ...]
    
    # Check if a state is valid
    if is_valid_state('CA'):
        ...
    
    # Get cities for a state
    cities = get_valid_cities('CA')  # ['Los Angeles', 'San Francisco', ...]
"""

import json
import os
from typing import List, Dict, Optional, Any
from functools import lru_cache


# Path to the jurisdictions config file
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "jurisdictions.json")


@lru_cache(maxsize=1)
def _load_config() -> Dict[str, Any]:
    """Load and cache the jurisdictions config file."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Jurisdictions config file not found: {CONFIG_FILE}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in jurisdictions config: {e}")


def get_config() -> Dict[str, Any]:
    """Get the full config dictionary."""
    return _load_config()


# ==================== States ====================

def get_valid_states() -> List[str]:
    """Get list of valid state codes (e.g., ['AL', 'AK', 'AZ', ...])."""
    config = _load_config()
    return list(config.get("states", {}).keys())


def get_state_name(state_code: str) -> Optional[str]:
    """Get full name for a state code (e.g., 'CA' -> 'California')."""
    config = _load_config()
    state_data = config.get("states", {}).get(state_code.upper())
    return state_data.get("name") if state_data else None


def is_valid_state(state_code: str) -> bool:
    """Check if a state code is valid."""
    if not state_code:
        return False
    return state_code.upper() in get_valid_states()


# ==================== Cities ====================

def get_valid_cities(state_code: str) -> List[str]:
    """Get list of valid cities for a state."""
    config = _load_config()
    state_data = config.get("states", {}).get(state_code.upper(), {})
    return state_data.get("cities", [])


def get_all_cities() -> List[str]:
    """Get list of all cities across all states."""
    config = _load_config()
    all_cities = []
    for state_data in config.get("states", {}).values():
        all_cities.extend(state_data.get("cities", []))
    return list(set(all_cities))  # Remove duplicates


def is_valid_city(city: str, state_code: Optional[str] = None) -> bool:
    """Check if a city is valid, optionally within a specific state."""
    if not city:
        return False
    
    if state_code:
        valid_cities = get_valid_cities(state_code)
        return city in valid_cities
    else:
        # Check against all cities
        return city in get_all_cities()


# ==================== Categories ====================

def get_valid_categories() -> List[str]:
    """Get list of valid categories (e.g., ['Federal', 'State', 'Local'])."""
    config = _load_config()
    return config.get("categories", ["Federal", "State", "Local"])


def is_valid_category(category: str) -> bool:
    """Check if a category is valid."""
    if not category:
        return False
    return category in get_valid_categories()


# ==================== Document Types ====================

def get_valid_doc_types() -> List[str]:
    """Get list of valid document types."""
    config = _load_config()
    return config.get("doc_types", [])


def is_valid_doc_type(doc_type: str) -> bool:
    """Check if a document type is valid."""
    if not doc_type:
        return False
    return doc_type.lower() in get_valid_doc_types()


# ==================== Tax Types ====================

def get_valid_tax_types() -> List[str]:
    """Get list of valid tax types."""
    config = _load_config()
    return config.get("tax_types", [])


def is_valid_tax_type(tax_type: str) -> bool:
    """Check if a tax type is valid."""
    if not tax_type:
        return False
    return tax_type.lower() in get_valid_tax_types()


# ==================== Utility ====================

def get_states_with_cities() -> Dict[str, Dict[str, Any]]:
    """Get full states dictionary with names and cities."""
    config = _load_config()
    return config.get("states", {})


def reload_config():
    """Clear cache and reload config (useful if file is updated)."""
    _load_config.cache_clear()
