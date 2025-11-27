"""
Pricing configuration for dynamic pricing engine.
Defines season multipliers, occupancy thresholds, and discount rules.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Tuple


class Season(str, Enum):
    """Season types for pricing multipliers"""
    PEAK = "peak"          # Major holidays, special events
    HIGH = "high"          # Summer, popular vacation periods
    REGULAR = "regular"    # Normal business days
    LOW = "low"            # Off-season, weekdays


class DiscountType(str, Enum):
    """Discount types"""
    EARLY_BIRD = "early_bird"      # Book X days in advance
    LAST_MINUTE = "last_minute"    # Book within Y days
    EXTENDED_STAY = "extended_stay"  # Stay X+ nights
    NONE = "none"


# Season date ranges (month, day tuples)
# Format: (start_month, start_day, end_month, end_day)
SEASON_DATE_RANGES: Dict[Season, list[Tuple[int, int, int, int]]] = {
    Season.PEAK: [
        (12, 20, 1, 5),    # Christmas/New Year
        (7, 1, 7, 15),     # July 4th period
        (11, 22, 11, 28),  # Thanksgiving week
    ],
    Season.HIGH: [
        (6, 1, 8, 31),     # Summer season (excluding peak periods)
        (3, 1, 4, 15),     # Spring break season
    ],
    Season.LOW: [
        (1, 15, 2, 28),    # Post-holiday winter
        (9, 1, 10, 31),    # Fall shoulder season
    ],
    # REGULAR fills the gaps (everything else)
}


# Season multipliers applied to base price
SEASON_MULTIPLIERS: Dict[Season, float] = {
    Season.PEAK: 1.5,      # 50% increase during peak
    Season.HIGH: 1.25,     # 25% increase during high season
    Season.REGULAR: 1.0,   # Base price
    Season.LOW: 0.85,      # 15% discount during low season
}


# Occupancy thresholds and multipliers
# Format: (threshold percentage, multiplier)
# Applied based on percentage of rooms already booked
OCCUPANCY_THRESHOLDS: list[Tuple[float, float]] = [
    (0.90, 1.4),   # 90%+ occupancy: 40% surge
    (0.80, 1.3),   # 80-89% occupancy: 30% surge
    (0.70, 1.2),   # 70-79% occupancy: 20% surge
    (0.60, 1.15),  # 60-69% occupancy: 15% surge
    (0.50, 1.1),   # 50-59% occupancy: 10% surge
    (0.0, 1.0),    # Below 50%: no surge
]


# Discount rules
# Early bird: book 30+ days in advance
EARLY_BIRD_DAYS = 30
EARLY_BIRD_DISCOUNT = 0.10  # 10% off

# Last minute: book within 3 days
LAST_MINUTE_DAYS = 3
LAST_MINUTE_DISCOUNT = 0.15  # 15% off (clear inventory)

# Extended stay: 7+ nights
EXTENDED_STAY_NIGHTS = 7
EXTENDED_STAY_DISCOUNT = 0.12  # 12% off


def get_season_for_date(date: datetime) -> Season:
    """
    Determine season for a given date based on configured date ranges.
    
    Args:
        date: Date to check
        
    Returns:
        Season enum value
    """
    month = date.month
    day = date.day
    
    # Check peak season first (highest priority)
    for start_month, start_day, end_month, end_day in SEASON_DATE_RANGES[Season.PEAK]:
        if _is_date_in_range(month, day, start_month, start_day, end_month, end_day):
            return Season.PEAK
    
    # Check high season
    for start_month, start_day, end_month, end_day in SEASON_DATE_RANGES[Season.HIGH]:
        if _is_date_in_range(month, day, start_month, start_day, end_month, end_day):
            return Season.HIGH
    
    # Check low season
    for start_month, start_day, end_month, end_day in SEASON_DATE_RANGES[Season.LOW]:
        if _is_date_in_range(month, day, start_month, start_day, end_month, end_day):
            return Season.LOW
    
    # Default to regular season
    return Season.REGULAR


def _is_date_in_range(
    month: int,
    day: int,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int
) -> bool:
    """
    Check if a date falls within a date range.
    Handles year wraparound (e.g., Dec 20 - Jan 5).
    
    Args:
        month: Month to check (1-12)
        day: Day to check (1-31)
        start_month: Range start month
        start_day: Range start day
        end_month: Range end month
        end_day: Range end day
        
    Returns:
        True if date is in range
    """
    if start_month <= end_month:
        # Normal range within same year
        if month < start_month or month > end_month:
            return False
        if month == start_month and day < start_day:
            return False
        if month == end_month and day > end_day:
            return False
        return True
    else:
        # Wraparound range (e.g., Dec - Jan)
        if month > end_month and month < start_month:
            return False
        if month == start_month and day < start_day:
            return False
        if month == end_month and day > end_day:
            return False
        return True


def get_occupancy_multiplier(occupancy_rate: float) -> float:
    """
    Get pricing multiplier based on occupancy rate.
    
    Args:
        occupancy_rate: Percentage of rooms booked (0.0 - 1.0)
        
    Returns:
        Multiplier to apply to price
    """
    for threshold, multiplier in OCCUPANCY_THRESHOLDS:
        if occupancy_rate >= threshold:
            return multiplier
    
    # Fallback (should not reach here with proper config)
    return 1.0


def calculate_discount_multiplier(
    discount_type: DiscountType,
    days_until_checkin: int,
    nights_stay: int
) -> Tuple[float, str]:
    """
    Calculate discount multiplier and reason.
    
    Args:
        discount_type: Type of discount to apply
        days_until_checkin: Days from now until check-in
        nights_stay: Number of nights for the stay
        
    Returns:
        Tuple of (multiplier, discount_reason)
        multiplier is (1 - discount_percentage)
    """
    if discount_type == DiscountType.EARLY_BIRD and days_until_checkin >= EARLY_BIRD_DAYS:
        return (1.0 - EARLY_BIRD_DISCOUNT, f"Early bird ({EARLY_BIRD_DAYS}+ days advance)")
    
    if discount_type == DiscountType.LAST_MINUTE and days_until_checkin <= LAST_MINUTE_DAYS:
        return (1.0 - LAST_MINUTE_DISCOUNT, f"Last minute (≤{LAST_MINUTE_DAYS} days)")
    
    if discount_type == DiscountType.EXTENDED_STAY and nights_stay >= EXTENDED_STAY_NIGHTS:
        return (1.0 - EXTENDED_STAY_DISCOUNT, f"Extended stay ({EXTENDED_STAY_NIGHTS}+ nights)")
    
    return (1.0, "No discount applied")
