{ pkgs, config, lib, ... }:

let
  package = import ./package.nix { inherit pkgs; };
  description = "Telegram bot that keeps track of your debts";

  cfg = config.services.pythonTelegramBots.accountant-telegram-bot;
in
{
  options = {
    services.pythonTelegramBots.accountant-telegram-bot = {
      enable = lib.mkEnableOption description;

      stateDir = lib.mkOption {
        type = lib.types.str;
        default = "/var/lib/pytelegrambots/accountant-telegram-bot";
        description = "Data directory of the bot.";
      };

      configDir = lib.mkOption {
        type = lib.types.str;
        default = "/etc/pytelegrambots/accountant-telegram-bot";
        description = "Config directory of the bot.";
      };
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

        CONFIG=${configPath}/config
        if [ ! -f $CONFIG ]
        then
          echo "Config file at $CONFIG doesn't exist"
          exit 1
        fi

        export DATABASE_PATH=${cfg.stateDir}/db.db
        mkdir -p ${cfg.stateDir}

        . $CONFIG

        ${package}/bin/accountant-telegram-bot
      '';
    };
  };
}
