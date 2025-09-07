#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.rules import AdmissionRuleSet
from sqlalchemy import distinct


def list_programs():
    """List all unique program names from the database."""
    session = SessionLocal()
    try:
        # Query distinct rule set names
        programs = session.query(distinct(AdmissionRuleSet.name)).filter(
            AdmissionRuleSet.name.isnot(None)
        ).all()
        
        print("数据库中的录取规则集列表:")
        print("=" * 50)
        
        if not programs:
            print("未找到任何录取规则数据")
            return []
        
        program_list = []
        for program in programs:
            program_name = program[0]
            if program_name and program_name.strip():
                print(f"- {program_name}")
                program_list.append(program_name)
        
        print(f"\n总共找到 {len(program_list)} 个录取规则集")
        return program_list
        
    except Exception as e:
        print(f"查询数据库时出错: {e}")
        return []
    finally:
        session.close()


if __name__ == "__main__":
    list_programs()
