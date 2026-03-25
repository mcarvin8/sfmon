#!/usr/bin/env python3
"""
Minimal Permission Sets Report Generator

This utility script analyzes Salesforce permission set metadata files to identify
permission sets that have very few permissions configured (5 or fewer). These "minimal"
permission sets may be candidates for consolidation to reduce org complexity and improve
maintainability.

Purpose:
    - Identify permission sets with 5 or fewer actual permissions
    - Generate JSON report for review and potential consolidation planning
    - Should be run in a CI/CD pipeline after retrieving production metadata

Pipeline Integration:
    1. Scheduled pipeline retrieves permission set metadata from production org
    2. This script analyzes the metadata files
    3. Generates minimal-perm-sets.json (default under src/sfmon/tech_debt/)
    4. Report is consumed by tech-debt monitoring service
    5. Metrics exposed to Grafana for visualization and alerting

Permission Detection Logic:
    The script counts all actual permission elements in each permission set.
    Metadata-only elements are ignored:
    - label, description, hasActivationRequired, license, custom
    
    All other nested elements are counted as permissions (e.g., objectPermissions,
    userPermissions, fieldPermissions, etc.). If a permission set has 5 or fewer
    permission elements, it's considered "minimal" and flagged for potential consolidation.

Output Format:
    JSON file containing:
    - scan_date: ISO timestamp of analysis
    - total_permission_sets: Count of all permission sets analyzed
    - threshold: Maximum number of permissions to be considered minimal (5)
    - minimal_permission_sets: Array of permission sets with 5 or fewer permissions
        * name: Permission set label
        * file_path: Metadata filename
        * permission_count: Number of permission elements found
    - error_count: Number of parsing errors
    - metadata_source: Source directory path

Usage:
    python determine_minimal_perm_sets.py [--metadata-dir path] [--output path] [--threshold N]
    
Arguments:
    --metadata-dir: Directory containing .permissionset-meta.xml files
                   (default: ./force-app/main/default/permissionsets)
    --output: Output path for JSON report
             (default: ./src/sfmon/tech_debt/minimal-perm-sets.json)
    --threshold: Maximum number of permissions to be considered minimal
                (default: 5)

Exit Codes:
    0: Success
    1: Metadata directory not found or other error
"""

import os
import json
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def analyze_permission_sets(metadata_dir, threshold=5):
    """
    Analyze permission sets in the metadata directory to identify minimal ones.
    
    Args:
        metadata_dir (str): Path to directory containing permission set XML files
        threshold (int): Maximum number of permissions to be considered minimal (default: 5)
        
    Returns:
        dict: Analysis results with minimal permission sets list
    """
    
    # Metadata-only elements that don't indicate actual permissions
    # These are basic fields that define the permission set but don't grant access
    metadata_only_elements = {
        'label',
        'description', 
        'hasActivationRequired',
        'license'
    }
    
    minimal_permission_sets = []
    total_count = 0
    error_count = 0
    
    print(f"Scanning permission sets in: {metadata_dir}")
    print(f"Threshold for minimal permission sets: {threshold} permissions or fewer")
    
    # Scan all .xml files in the permission sets directory
    for file_path in Path(metadata_dir).glob("*.xml"):
        total_count += 1
        filename = file_path.name
        
        try:
            # Parse the XML file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract namespace from root tag if present
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'
            
            # Count actual permission elements (non-metadata elements)
            permission_count = 0
            for child in root:
                # Get element name without namespace
                element_name = child.tag.replace(namespace, '')
                
                # If element is not in metadata-only list, it's a permission element
                if element_name not in metadata_only_elements:
                    permission_count += 1
            
            # If permission count is at or below threshold, it's minimal
            if permission_count <= threshold:
                # Extract the label for better identification
                label_element = root.find(f'{namespace}label')
                
                permission_set_name = label_element.text if label_element is not None else filename
                
                # Remove .permissionset-meta.xml extension from filename for cleaner reporting
                clean_filename = filename.replace('.permissionset-meta.xml', '') if filename.endswith('.permissionset-meta.xml') else filename
                
                minimal_permission_set = {
                    'name': permission_set_name,
                    'file_path': clean_filename,
                    'permission_count': permission_count
                }
                
                minimal_permission_sets.append(minimal_permission_set)
                print(f"  MINIMAL: {permission_set_name} ({filename}) - {permission_count} permissions")
            else:
                print(f"  NORMAL: {filename} - {permission_count} permissions")
            
        except ET.ParseError as e:
            print(f"  ERROR: Failed to parse XML file {filename}: {e}")
            error_count += 1
        except Exception as e:
            print(f"  ERROR: Failed to process file {filename}: {e}")
            error_count += 1
    
    # Sort minimal permission sets alphabetically by name
    minimal_permission_sets.sort(key=lambda x: x['name'].lower())
    
    return {
        'scan_date': datetime.now(timezone.utc).isoformat(),
        'total_permission_sets': total_count,
        'threshold': threshold,
        'minimal_permission_sets': minimal_permission_sets,
        'error_count': error_count,
        'metadata_source': str(metadata_dir)
    }


def main():
    """Main function to generate the minimal permission sets report."""
    
    parser = argparse.ArgumentParser(description='Generate minimal permission sets report')
    parser.add_argument('--metadata-dir', 
                       default='./force-app/main/default/permissionsets',
                       help='Directory containing permission set XML files (default: ./force-app/main/default/permissionsets)')
    parser.add_argument('--output', 
                       default='./src/sfmon/tech_debt/minimal-perm-sets.json',
                       help='Output file path for the report (default: ./src/sfmon/tech_debt/minimal-perm-sets.json)')
    parser.add_argument('--threshold',
                       type=int,
                       default=5,
                       help='Maximum number of permissions to be considered minimal (default: 5)')
    
    args = parser.parse_args()
    
    # Validate threshold
    if args.threshold < 0:
        print(f"Error: Threshold must be a non-negative number")
        return 1
    
    # Check if metadata directory exists
    if not os.path.exists(args.metadata_dir):
        print(f"Error: Metadata directory not found: {args.metadata_dir}")
        print("Make sure to retrieve permission set metadata from Salesforce first")
        return 1
    
    # Analyze permission sets
    print("Starting permission sets analysis...")
    results = analyze_permission_sets(args.metadata_dir, args.threshold)
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate report
    print(f"\nGenerating report: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    minimal_cnt = len(results['minimal_permission_sets'])
    total_count = results['total_permission_sets']
    error_count = results['error_count']
    threshold = results['threshold']
    
    print(f"\n=== ANALYSIS COMPLETE ===")
    print(f"Total permission sets: {total_count}")
    print(f"Minimal permission sets (<= {threshold} permissions): {minimal_cnt}")
    print(f"Percentage minimal: {minimal_cnt/total_count*100:.1f}%" if total_count > 0 else "N/A")
    print(f"Parse errors: {error_count}")
    print(f"Report saved to: {args.output}")
    
    # Show breakdown by permission count
    if minimal_cnt > 0:
        print(f"\n=== BREAKDOWN BY PERMISSION COUNT ===")
        count_breakdown = {}
        for perm_set in results['minimal_permission_sets']:
            count = perm_set['permission_count']
            count_breakdown[count] = count_breakdown.get(count, 0) + 1
        
        for count in sorted(count_breakdown.keys()):
            print(f"  {count} permissions: {count_breakdown[count]} permission sets")
    
    return 0


if __name__ == '__main__':
    exit(main())
