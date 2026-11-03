#!/bin/zsh
cd "${0:A:h}"
python3 tools/check_fidelity.py --full
result=$?
echo ""
echo "Fidelity checks exited with status $result. Reports are in standalone/replica/reports."
if [[ -t 0 ]]; then
  read -k 1 "?Press any key to close."
fi
exit $result
