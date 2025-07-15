{
  description = "Telegram bot that keeps track of your debts";

  inputs = {
    nixpkgs.url = github:nixos/nixpkgs/nixos-unstable;
    flake-utils.url = github:numtide/flake-utils;
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
    in
    {
      packages = {
        accountant-telegram-bot = pkgs.callPackage ./package.nix { };
        default = self.packages.${system}.accountant-telegram-bot;
      };
    })
    //
    {
      nixosModules = {
        accountant-telegram-bot = import ./nixos.nix;
        default = self.nixosModules.accountant-telegram-bot;
      };
    };
}
