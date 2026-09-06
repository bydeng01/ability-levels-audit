# The frozen offline environment for this study.
#
#   docker build -t ability-levels-audit .
#   docker run --rm ability-levels-audit                              # offline suite
#   docker run --rm ability-levels-audit python analysis/analyze.py   # the numbers
#
# Python 3.12.8 is the interpreter the protocol froze (protocol/decisions-log.md);
# requirements.txt carries the exact dependency pins. Nothing reachable from here
# makes a provider call and no key is baked into the image. The paid run is an
# operator sequence, not a container entrypoint: it requires a clean worktree and
# a prereg-final-* tag at HEAD, which a copied build context cannot certify.
FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /study

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "pytest", "tests/", "-q"]
