# Review records

`GSTACK_PEER_REVIEW_DIR` should point here, or at another directory that outlives the
session. It has no default: see EV-009 in `DESIGN.md` for the review whose record was lost
to one.

    GSTACK_PEER_REVIEW_DIR="$(git rev-parse --show-toplevel)/reviews"

A directory here holding only a `RECONSTRUCTION.md` is an account of a review assembled
after its record was lost. It is not a record and should not be read as one.
