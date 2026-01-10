"""Proximity validation for adjacent segments."""

import sqlite3

from bigcontext_mcp.db.queries import get_adjacent_segments, get_segment_by_id


def validate_proximity(
    conn: sqlite3.Connection,
    base_segment_id: int,
    target_segment_id: int,
    max_distance: int = 1,
) -> dict:
    """
    Validate that two segments are within proximity constraint.

    Args:
        conn: Database connection.
        base_segment_id: The anchor segment ID.
        target_segment_id: The segment being referenced.
        max_distance: Maximum allowed segment distance (0 = same, 1 = adjacent).

    Returns:
        Dict with validation status and details.
    """
    base_segment = get_segment_by_id(conn, base_segment_id)
    target_segment = get_segment_by_id(conn, target_segment_id)

    if not base_segment:
        return {
            "is_valid": False,
            "base_segment_id": base_segment_id,
            "target_segment_id": target_segment_id,
            "distance": None,
            "max_allowed": max_distance,
            "violation": f"Base segment {base_segment_id} not found",
        }

    if not target_segment:
        return {
            "is_valid": False,
            "base_segment_id": base_segment_id,
            "target_segment_id": target_segment_id,
            "distance": None,
            "max_allowed": max_distance,
            "violation": f"Target segment {target_segment_id} not found",
        }

    # Check if same document
    if base_segment["document_id"] != target_segment["document_id"]:
        return {
            "is_valid": False,
            "base_segment_id": base_segment_id,
            "target_segment_id": target_segment_id,
            "distance": None,
            "max_allowed": max_distance,
            "violation": "Segments are from different documents",
        }

    # Calculate distance
    distance = abs(base_segment["position"] - target_segment["position"])

    is_valid = distance <= max_distance

    return {
        "is_valid": is_valid,
        "base_segment_id": base_segment_id,
        "target_segment_id": target_segment_id,
        "distance": distance,
        "max_allowed": max_distance,
        "violation": None if is_valid else f"Distance {distance} exceeds max {max_distance}",
    }


def get_adjacent_segment_ids(
    conn: sqlite3.Connection,
    base_segment_id: int,
    max_distance: int = 1,
) -> list[int]:
    """
    Get segment IDs within proximity constraint of a base segment.

    Args:
        conn: Database connection.
        base_segment_id: The anchor segment ID.
        max_distance: Maximum distance from base.

    Returns:
        List of adjacent segment IDs.
    """
    adjacent = get_adjacent_segments(conn, base_segment_id, max_distance)
    return [seg["id"] for seg in adjacent]
