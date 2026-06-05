#!/bin/bash
# 星海理事会 — 环境初始化脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== 星海理事会 环境初始化 ==="
echo "项目路径: $PROJECT_DIR"
echo ""

# 1. Python 虚拟环境
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "[1/4] 创建 Python 虚拟环境..."
    python3 -m venv "$PROJECT_DIR/.venv"
else
    echo "[1/4] 虚拟环境已存在，跳过"
fi

# 2. 安装依赖
echo "[2/4] 安装 Python 依赖..."
source "$PROJECT_DIR/.venv/bin/activate"
pip install -r "$PROJECT_DIR/requirements.txt" -q

# 3. 验证
echo "[3/4] 验证依赖..."
python3 -c "import yaml, git, filelock; print('  pyyaml ✓  gitpython ✓  filelock ✓')"

# 4. Git remote
echo "[4/4] 检查 Git remote..."
cd "$PROJECT_DIR"
if git remote get-url origin &>/dev/null; then
    echo "  Git remote origin 已配置: $(git remote get-url origin)"
else
    echo "  请手动配置 Git remote:"
    echo "    git remote add origin ~/git-repos/star-council.git"
fi

echo ""
echo "=== 初始化完成 ==="
echo "激活虚拟环境: source $PROJECT_DIR/.venv/bin/activate"
echo "测试理事:    python src/councilor.py experiment"
