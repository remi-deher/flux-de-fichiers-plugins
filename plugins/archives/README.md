# Archives (`archives`)

`archives.extract` extrait une archive (7z, RAR, ZIP, TAR…) avec 7-Zip et poursuit le flux sur le plus gros fichier vidéo qu'elle contient (les échantillons « sample » sont écartés). Un fichier qui n'est pas une archive passe tel quel.

Placez le bloc **juste après l'entrée** : il déclare `acceptsNonMedia`, si bien que le flux tolère qu'une archive ne soit pas reconnue par la sonde ; le fichier extrait est inspecté ensuite. Pensez à ajouter les extensions d'archive (`rar`, `7z`, `zip`) aux extensions de la bibliothèque. Une archive protégée par mot de passe échoue sans attendre.

Outil : `7zip`, via le script [`scripts/archives.py`](scripts/archives.py).
