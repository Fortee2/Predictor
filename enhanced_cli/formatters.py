"""
Data formatting utilities for consistent presentation.

This module provides functions for formatting various types of data 
(dates, numbers, monetary values, etc.) consistently across the application.
"""

from typing import Union, Optional, Any, Dict, List
from decimal import Decimal
from datetime import datetime, date


def format_date(dt: Union[datetime, date, str, None], format_str: str = '%Y-%m-%d') -> str:
    """
    Format a date or datetime object to a string.
    
    Args:
        dt: Date or datetime object, date string, or None
        format_str: Format string for strftime
        
    Returns:
        Formatted date string or empty string if dt is None
    """
    if dt is None:
        return ""
    
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d')
        except ValueError:
            return dt  # Return as-is if parsing fails
    
    if isinstance(dt, (datetime, date)):
        return dt.strftime(format_str)
    
    return str(dt)  # Fall back to string conversion


def format_number(value: Union[int, float, Decimal, None], decimal_places: int = 2) -> str:
    """
    Format a number with consistent decimal places.
    
    Args:
        value: Number to format
        decimal_places: Number of decimal places to include
        
    Returns:
        Formatted number string or empty string if value is None
    """
    if value is None:
        return ""
        
    # Convert to float to ensure consistent handling
    try:
        value_float = float(value)
        return f"{value_float:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(value)


def format_currency(
    value: Union[int, float, Decimal, None], 
    currency_symbol: str = '$', 
    decimal_places: int = 2,
    show_positive: bool = False
) -> str:
    """
    Format a monetary value with currency symbol.
    
    Args:
        value: Monetary value to format
        currency_symbol: Currency symbol to prepend
        decimal_places: Number of decimal places to include
        show_positive: Whether to add '+' for positive values
        
    Returns:
        Formatted currency string or empty string if value is None
    """
    if value is None:
        return ""
    
    try:
        value_float = float(value)
        formatted = f"{abs(value_float):,.{decimal_places}f}"
        
        if value_float > 0:
            prefix = '+' if show_positive else ''
            return f"{prefix}{currency_symbol}{formatted}"
        elif value_float < 0:
            return f"-{currency_symbol}{formatted}"
        else:
            return f"{currency_symbol}{formatted}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(
    value: Union[int, float, Decimal, None], 
    decimal_places: int = 2, 
    include_symbol: bool = True, 
    show_positive: bool = False
) -> str:
    """
    Format a value as a percentage.
    
    Args:
        value: Value to format as percentage
        decimal_places: Number of decimal places to include
        include_symbol: Whether to include the '%' symbol
        show_positive: Whether to add '+' for positive values
        
    Returns:
        Formatted percentage string or empty string if value is None
    """
    if value is None:
        return ""
    
    try:
        value_float = float(value)
        formatted = f"{abs(value_float):.{decimal_places}f}"
        symbol = '%' if include_symbol else ''
        
        if value_float > 0:
            prefix = '+' if show_positive else ''
            return f"{prefix}{formatted}{symbol}"
        elif value_float < 0:
            return f"-{formatted}{symbol}"
        else:
            return f"{formatted}{symbol}"
    except (ValueError, TypeError):
        return str(value)


def truncate_string(text: str, max_length: int = 50, ellipsis: str = '...') -> str:
    """
    Truncate a string to a maximum length with ellipsis.
    
    Args:
        text: String to truncate
        max_length: Maximum length
        ellipsis: Ellipsis string to append
        
    Returns:
        Truncated string
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
        
    return text[:max_length - len(ellipsis)] + ellipsis


def format_table_row(
    row_data: Dict[str, Any], 
    column_formats: Dict[str, Dict[str, Any]]
) -> List[str]:
    """
    Format a row of data for table display according to column formats.
    
    Args:
        row_data: Dictionary of column names to values
        column_formats: Dictionary of column names to format specifications
                        Each format spec can include:
                        - 'type': 'date', 'number', 'currency', 'percentage', or 'string'
                        - 'format_args': dict of args for the corresponding format function
        
    Returns:
        List of formatted cell values
    """
    formatted_row = []
    
    for col_name, format_spec in column_formats.items():
        value = row_data.get(col_name)
        
        if value is None:
            formatted_row.append("")
            continue
        
        format_type = format_spec.get('type', 'string')
        format_args = format_spec.get('format_args', {})
        
        if format_type == 'date':
            formatted_row.append(format_date(value, **format_args))
        elif format_type == 'number':
            formatted_row.append(format_number(value, **format_args))
        elif format_type == 'currency':
            formatted_row.append(format_currency(value, **format_args))
        elif format_type == 'percentage':
            formatted_row.append(format_percentage(value, **format_args))
        elif format_type == 'string' and isinstance(value, str):
            max_length = format_args.get('max_length')
            if max_length:
                formatted_row.append(truncate_string(value, max_length, format_args.get('ellipsis', '...')))
            else:
                formatted_row.append(value)
        else:
            formatted_row.append(str(value))
    
    return formatted_row
