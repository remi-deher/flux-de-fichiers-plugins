# Exemple d'application déclarative installable

[manifest.json](manifest.json) présente l'app ;
[installation.json](installation.json) déclare ses composants exacts et son
point d'entrée de flow. Le paquet est déclaratif, destiné au futur frontend
Leptos et au runtime Rust ; il ne contient aucun nouveau code applicatif.

Le [contrat d'installation](../../../../docs/contrat-packs.md) décrit activation,
mise à jour, échec et désinstallation avec conservation des médias. Le cycle est
indépendant de l'exécution d'un flow. `runtimeImplemented: false` signifie qu'aucun
installeur ni bundle publié n'est livré, et aucune app n'a été installée.
