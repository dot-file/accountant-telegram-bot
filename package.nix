{ pkgs }:

pkgs.writers.writePython3Bin "librescore-telegram-bot"
{
  libraries = with pkgs.python3Packages; [
    pytelegrambotapi
    requests
  ];
  doCheck = false;
} ./src/main.py
