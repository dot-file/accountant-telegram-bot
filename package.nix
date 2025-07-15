{ pkgs }:

pkgs.writers.writePython3Bin "accountant-telegram-bot"
{
  libraries = with pkgs.python3Packages; [
    pytelegrambotapi
    requests
  ];
  doCheck = false;
} ./src/main.py
