{ pkgs, config, lib, ... }:

let
  package = import ./package.nix { inherit pkgs; };
  description = "Telegram bot that keeps track of your debts";
  configPath = "/etc/pytelegrambots/accountant-telegram-bot/config";

  cfg = config.services.pythonTelegramBots.accountant-telegram-bot;
in
{
  options = {
    services.pythonTelegramBots.accountant-telegram-bot = {
      enable = lib.mkEnableOption description;
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services."accountant-telegram-bot" = {
      inherit description;
      after = [ "network-online.target" ];
      wantedBy = [ "multi-user.target" ];
      preStart = "while ! ${pkgs.iputils}/bin/ping -c1 1.1.1.1; do sleep 1; done";

      serviceConfig = {
        Restart = "always";
      };

      script = ''
        set -a

        CONFIG=${configPath}
        if [ ! -f $CONFIG ]
        then
          echo "Config file at $CONFIG doesn't exist"
          exit 1
        fi

        . $CONFIG

        ${package}/bin/accountant-telegram-bot
      '';
    };
  };
}
