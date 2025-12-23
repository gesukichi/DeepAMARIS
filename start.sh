#!/bin/bash

echo ""
echo "Restoring frontend npm packages"
echo ""
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo "Failed to restore frontend npm packages"
    exit $?
fi

echo ""
echo "Building frontend"
echo ""
npm run build
if [ $? -ne 0 ]; then
    echo "Failed to build frontend"
    exit $?
fi

cd ..
. ./scripts/loadenv.sh

echo ""
echo "Starting backend"
echo ""
export PORT=${PORT:-8000}
./.venv/bin/python -m quart run --port=$PORT --host=0.0.0.0 --reload
if [ $? -ne 0 ]; then
    echo "Failed to start backend"
    exit $?
fi
