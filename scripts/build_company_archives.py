"""公司归档入口委托证据驱动生成器。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.rebuild_verified_drive_dossiers import main
if __name__=='__main__': main()
