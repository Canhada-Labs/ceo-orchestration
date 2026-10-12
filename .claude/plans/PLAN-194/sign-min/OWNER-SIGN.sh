#!/bin/bash
# CEREMONY-LINT: handwritten-exception: molde SIGN mínimo que assina o sentinel do pacote (PLAN-194, S363)
case "${BASH_SOURCE[0]}" in */*) ;; *) printf '%s\n' 'SIGN-RECUSA: a entrada não foi chamada por um caminho com «/»' 'Pare e chame o CEO.'; exit 1 ;; esac  # E:src
case ":${PATH-}:" in *::*|*:[!/]*) printf '%s\n' 'SIGN-RECUSA: o PATH tem entrada vazia ou que não começa com «/»' 'Pare e chame o CEO.'; exit 1 ;; esac  # E:path
command -v python3 >/dev/null 2>&1 || { printf '%s\n' 'SIGN-RECUSA: python3 ausente no PATH' 'Pare e chame o CEO.'; exit 1; }  # E:py
re='^--nucleo-sha256=[0-9a-f]{64}$'
[[ ${1-} =~ $re ]] || { printf '%s\n' 'SIGN-RECUSA: o 1.º argumento não é --nucleo-sha256= com 64 hex minúsculos' 'Pare e chame o CEO.'; exit 1; }  # E:args
nucleo="${BASH_SOURCE[0]%/*}/sign_min.py"
s=$(python3 -I -B -c 'import hashlib,sys;sys.stdout.write(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$nucleo" 2>/dev/null)
[[ "--nucleo-sha256=$s" == "$1" ]] || { printf '%s\n' 'SIGN-RECUSA: o núcleo ao lado da entrada não tem o sha256 informado' 'Pare e chame o CEO.'; exit 1; }  # E:sha
shift
exec python3 -I -B "$nucleo" "$@"
