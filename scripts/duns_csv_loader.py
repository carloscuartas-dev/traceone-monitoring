#!/usr/bin/env python3
"""
DUNS CSV Loader Utility

This utility helps load DUNS numbers from CSV files for real-time testing.
Supports various CSV formats and provides validation.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any
import click
import structlog

logger = structlog.get_logger(__name__)


class DunsCSVLoader:
    """Utility class for loading DUNS numbers from CSV files"""
    
    def __init__(self):
        self.valid_duns = []
        self.invalid_duns = []
        self.metadata = {}
    
    def is_valid_duns(self, duns: str) -> bool:
        """
        Validate DUNS number format
        
        Args:
            duns: DUNS number to validate
            
        Returns:
            True if valid DUNS format
        """
        # Remove any non-digit characters
        clean_duns = ''.join(c for c in str(duns) if c.isdigit())
        
        # DUNS should be 9 digits
        return len(clean_duns) == 9 and clean_duns.isdigit()
    
    def clean_duns(self, duns: str) -> str:
        """
        Clean and format DUNS number
        
        Args:
            duns: Raw DUNS number
            
        Returns:
            Cleaned DUNS number
        """
        # Remove any non-digit characters and leading zeros
        clean = ''.join(c for c in str(duns) if c.isdigit())
        return clean.zfill(9)  # Pad to 9 digits
    
    def load_from_csv(
        self, 
        csv_file: str, 
        duns_column: str = "duns",
        has_header: bool = True
    ) -> List[str]:
        """
        Load DUNS numbers from CSV file
        
        Args:
            csv_file: Path to CSV file
            duns_column: Name or index of DUNS column
            has_header: Whether CSV has header row
            
        Returns:
            List of valid DUNS numbers
        """
        csv_path = Path(csv_file)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        duns_list = []
        invalid_count = 0
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter) if has_header else csv.reader(file, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        if has_header:
                            # Use column name
                            duns_value = row.get(duns_column)
                            if duns_value is None:
                                # Try common column name variations
                                for col_variant in ['DUNS', 'duns_number', 'duns_num', 'company_duns']:
                                    if col_variant in row:
                                        duns_value = row[col_variant]
                                        break
                        else:
                            # Use column index
                            col_index = int(duns_column) if duns_column.isdigit() else 0
                            duns_value = row[col_index]
                        
                        if duns_value and str(duns_value).strip():
                            duns_clean = self.clean_duns(duns_value)
                            
                            if self.is_valid_duns(duns_clean):
                                if duns_clean not in duns_list:  # Avoid duplicates
                                    duns_list.append(duns_clean)
                                    logger.debug("Valid DUNS loaded", 
                                               duns=duns_clean, 
                                               row=row_num)
                            else:
                                invalid_count += 1
                                self.invalid_duns.append({
                                    'row': row_num,
                                    'original': duns_value,
                                    'cleaned': duns_clean
                                })
                                logger.warning("Invalid DUNS format", 
                                             duns=duns_value, 
                                             row=row_num)
                        
                    except Exception as e:
                        logger.error("Error processing row", 
                                   row=row_num, 
                                   error=str(e))
                        continue
        
        except Exception as e:
            logger.error("Error reading CSV file", 
                       file=csv_file, 
                       error=str(e))
            raise
        
        logger.info("CSV loading completed",
                   file=csv_file,
                   valid_duns=len(duns_list),
                   invalid_duns=invalid_count,
                   total_processed=len(duns_list) + invalid_count)
        
        self.valid_duns = duns_list
        return duns_list
    
    def load_from_simple_csv(self, csv_file: str) -> List[str]:
        """
        Load DUNS from simple CSV (one DUNS per line or comma-separated)
        
        Args:
            csv_file: Path to simple CSV file
            
        Returns:
            List of valid DUNS numbers
        """
        csv_path = Path(csv_file)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        duns_list = []
        
        with open(csv_path, 'r') as file:
            content = file.read().strip()
            
            # Try different separators
            for separator in [',', '\n', ';', '\t']:
                if separator in content:
                    values = content.split(separator)
                    break
            else:
                # Single value
                values = [content]
            
            for value in values:
                value = value.strip()
                if value:
                    duns_clean = self.clean_duns(value)
                    if self.is_valid_duns(duns_clean) and duns_clean not in duns_list:
                        duns_list.append(duns_clean)
        
        logger.info("Simple CSV loading completed",
                   file=csv_file,
                   duns_count=len(duns_list))
        
        return duns_list
    
    def export_to_csv(self, duns_list: List[str], output_file: str):
        """
        Export DUNS list to CSV file
        
        Args:
            duns_list: List of DUNS numbers
            output_file: Output CSV file path
        """
        with open(output_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['duns'])  # Header
            for duns in duns_list:
                writer.writerow([duns])
        
        logger.info("DUNS exported to CSV", 
                   file=output_file, 
                   count=len(duns_list))


@click.group()
def cli():
    """DUNS CSV Loader Utility"""
    pass


@cli.command()
@click.argument('csv_file')
@click.option('--column', '-c', default='duns', help='DUNS column name or index')
@click.option('--no-header', is_flag=True, help='CSV has no header row')
@click.option('--output', '-o', help='Save valid DUNS to file')
def load(csv_file, column, no_header, output):
    """Load and validate DUNS from CSV file"""
    
    # Setup logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    loader = DunsCSVLoader()
    
    try:
        duns_list = loader.load_from_csv(
            csv_file, 
            column, 
            has_header=not no_header
        )
        
        click.echo(f"✅ Successfully loaded {len(duns_list)} valid DUNS numbers:")
        
        for i, duns in enumerate(duns_list, 1):
            click.echo(f"  {i:3d}. {duns}")
        
        if loader.invalid_duns:
            click.echo(f"\n⚠️  Found {len(loader.invalid_duns)} invalid DUNS:")
            for invalid in loader.invalid_duns[:5]:  # Show first 5
                click.echo(f"  Row {invalid['row']}: {invalid['original']} -> {invalid['cleaned']}")
            
            if len(loader.invalid_duns) > 5:
                click.echo(f"  ... and {len(loader.invalid_duns) - 5} more")
        
        if output:
            loader.export_to_csv(duns_list, output)
            click.echo(f"\n📄 Valid DUNS saved to: {output}")
        
        # Show command to use with real-time testing
        if duns_list:
            duns_args = ' '.join([f'-d {duns}' for duns in duns_list[:10]])  # Show first 10
            click.echo(f"\n🚀 Use with real-time testing:")
            click.echo(f"   python3 scripts/real_time_testing.py {duns_args}")
            
            if len(duns_list) > 10:
                click.echo(f"   (showing first 10 of {len(duns_list)} DUNS)")
    
    except Exception as e:
        click.echo(f"❌ Error loading CSV: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('csv_file')
def simple(csv_file):
    """Load DUNS from simple CSV (one per line or comma-separated)"""
    
    loader = DunsCSVLoader()
    
    try:
        duns_list = loader.load_from_simple_csv(csv_file)
        
        click.echo(f"✅ Loaded {len(duns_list)} DUNS numbers:")
        for duns in duns_list:
            click.echo(f"  {duns}")
        
        # Show command for real-time testing
        if duns_list:
            duns_args = ' '.join([f'-d {duns}' for duns in duns_list])
            click.echo(f"\n🚀 Use with real-time testing:")
            click.echo(f"   python3 scripts/real_time_testing.py {duns_args}")
    
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def create_sample():
    """Create sample CSV files for testing"""
    
    # Sample CSV with header
    sample_csv = """company_name,duns,industry
Apple Inc,123456789,Technology
Microsoft Corp,987654321,Technology
Amazon.com Inc,555666777,Retail
Google LLC,444555666,Technology
"""
    
    with open('sample_duns.csv', 'w') as f:
        f.write(sample_csv)
    
    # Simple CSV (one per line)
    simple_csv = """123456789
987654321
555666777
"""
    
    with open('simple_duns.csv', 'w') as f:
        f.write(simple_csv)
    
    click.echo("✅ Sample CSV files created:")
    click.echo("  📄 sample_duns.csv - CSV with headers")
    click.echo("  📄 simple_duns.csv - Simple format (one per line)")
    click.echo("\n🧪 Test with:")
    click.echo("  python3 scripts/duns_csv_loader.py load sample_duns.csv")
    click.echo("  python3 scripts/duns_csv_loader.py simple simple_duns.csv")


if __name__ == "__main__":
    cli()
