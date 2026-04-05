#!/usr/bin/env fish
set -l envfile (dirname (status -f))/../.env
if test -f $envfile
    for line in (cat $envfile)
        if string match -qr '^\s*#' -- $line
            continue
        end
        if test -z (string trim -- $line)
            continue
        end
        set -l kv (string split -m 1 '=' -- $line)
        if test (count $kv) -eq 2
            set -gx (string trim -- $kv[1]) (string trim -- $kv[2])
        end
    end
    echo "Loaded qbrain env from $envfile"
else
    echo "No .env found at $envfile"
end
