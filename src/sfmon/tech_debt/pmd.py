import os
import xml.etree.ElementTree as ET
from collections import defaultdict

from logger import logger
from gauges import (
    pmd_code_smells_gauge,
)

def monitor_pmd_code_smells(_sf):
    """
    Parse PMD XML report and set Prometheus gauge for rule violations.
    Runs once daily to monitor tech debt from PMD static analysis.

    Requires PMD_RULESET_PATH to point to the ruleset XML. All rules from that
    file are exposed on the gauge, including those with 0 violations in the report.
    If the variable is unset or the file is missing, exits quietly.

    Args:
        _sf: Salesforce connection (unused; scheduler passes the shared client).
    """
    try:
        ruleset_file_path = (os.getenv("PMD_RULESET_PATH") or "").strip()
        if not ruleset_file_path or not os.path.isfile(ruleset_file_path):
            logger.debug(
                "Skipping PMD monitoring: PMD_RULESET_PATH missing or file not found"
            )
            return

        logger.info("Monitoring PMD rule violations from XML report...")

        # PMD report file is in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pmd_file_path = os.path.join(script_dir, "pmd-report.xml")

        logger.debug("Parsing ruleset file at: %s", ruleset_file_path)
        ruleset_tree = ET.parse(ruleset_file_path)
        ruleset_root = ruleset_tree.getroot()

        # Extract namespace if present
        ruleset_namespace = ""
        if ruleset_root.tag.startswith("{"):
            ruleset_namespace = ruleset_root.tag.split("}")[0] + "}"

        expected_rules = set()
        for rule in ruleset_root.findall(f"{ruleset_namespace}rule"):
            rule_ref = rule.get("ref", "")
            if rule_ref:
                rule_name = rule_ref.split("/")[-1]
                expected_rules.add(rule_name)
                logger.debug("Found expected rule in ruleset: %s", rule_name)

        logger.info("Loaded %d rules from ruleset file", len(expected_rules))

        # Clear existing Prometheus gauge labels once at the start
        pmd_code_smells_gauge.clear()

        if not os.path.exists(pmd_file_path):
            logger.warning("PMD report file not found at: %s", pmd_file_path)
            # If ruleset exists, still set all rules to 0
            if expected_rules:
                for rule_name in expected_rules:
                    pmd_code_smells_gauge.labels(rule_name=rule_name).set(0)
                    logger.debug(
                        "PMD Rule Violation - %s: 0 violations (from ruleset, no report)",
                        rule_name,
                    )
            return

        logger.info("Found PMD report at: %s", pmd_file_path)

        # Parse the XML file
        tree = ET.parse(pmd_file_path)
        root = tree.getroot()

        # Count violations by rule name (code smell type)
        rule_names = defaultdict(int)

        # PMD XML has a namespace, so we need to handle it properly
        # Extract namespace from root tag if present
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"

        # PMD XML structure: <pmd><file><violation rule="RuleName">
        for file_element in root.findall(f"{namespace}file"):
            for violation in file_element.findall(f"{namespace}violation"):
                rule_name = violation.get("rule", "Unknown")
                rule_names[rule_name] += 1
                logger.debug("Found rule violation: %s", rule_name)

        # Set gauge values for each code smell type from the report
        total_violations = 0
        for rule_name, count in rule_names.items():
            pmd_code_smells_gauge.labels(rule_name=rule_name).set(count)
            total_violations += count
            logger.debug("PMD Rule Violation - %s: %d violations", rule_name, count)

        # Ensure all rules from the ruleset are present in the gauge, even if they have 0 violations
        for rule_name in expected_rules:
            if rule_name not in rule_names:
                pmd_code_smells_gauge.labels(rule_name=rule_name).set(0)
                logger.debug(
                    "PMD Rule Violation - %s: 0 violations (from ruleset)", rule_name
                )

        # Also set a total count gauge
        if total_violations > 0:
            pmd_code_smells_gauge.labels(rule_name="TOTAL").set(total_violations)

        logger.info(
            "PMD monitoring completed. Total violations: %d, Unique rules: %d, Ruleset rules: %d",
            total_violations,
            len(rule_names),
            len(expected_rules),
        )

    # pylint: disable=broad-except
    except ET.ParseError as e:
        logger.error("Error parsing PMD XML report: %s", e)
    except FileNotFoundError as e:
        logger.error("PMD report file not found: %s", e)
    except Exception as e:
        logger.error("Error monitoring PMD rule violations: %s", e)
