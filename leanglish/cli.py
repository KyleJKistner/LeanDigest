"""Public Leanglish entry point; legacy reading commands remain compatible."""
from __future__ import annotations
import argparse
import sys
from proofreader.cli import main as proofreader_main, parser as proofreader_parser


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args and args[0] == 'catalog':
            from proofreader.finding_catalog import main as catalog_main
            return catalog_main(args[1:], prog='leanglish catalog')
        if args and args[0] == 'audit-catalog':
            from proofreader.catalog_audit import main as audit_main
            return audit_main(args[1:], prog='leanglish audit-catalog')
        if args and args[0] == 'reading-kpis':
            from proofreader.reading_kpis import main as kpi_main
            return kpi_main(args[1:], prog='leanglish reading-kpis')
        if args in [['--help'], ['-h']]:
            parser = proofreader_parser('leanglish')
            parser.formatter_class = argparse.RawDescriptionHelpFormatter
            parser.epilog = ('Finding-level catalog commands:\n'
                '  leanglish catalog --help       Build from frozen local observations\n'
                '  leanglish audit-catalog SITE   Check every local link and inventory\n'
                '  leanglish reading-kpis DIR     Re-render every snapshot and measure the readings\n')
            parser.print_help()
            return 0
        return proofreader_main(args, prog='leanglish')
    except (ValueError, OSError) as exc:
        print('Leanglish: '+str(exc), file=sys.stderr)
        return 2
