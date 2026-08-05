# Castle-Combat

## Summary

A clone of the old arcade game [Rampart](https://en.wikipedia.org/wiki/Rampart_(video_game)). Up to four players build castle walls, place cannons inside these walls, and attack their enemies. If a player cannot build a complete wall around one of his castles, he loses. The last surviving player wins.

The game can be played by two people at the same computer or with up to 4 players of the network.

## Installation

Install with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install git+https://github.com/karlb/castle-combat.git
```

Then start the game with `castle-combat`.

To run it once without installing:

```sh
uvx --from git+https://github.com/karlb/castle-combat.git castle-combat
```

## Development

```sh
git clone git@github.com:karlb/castle-combat.git
cd castle-combat
uv run castle-combat
```

## Support

Please report bugs at https://github.com/karlb/castle-combat/issues.

## Author

Karl Bartel <karl42@gmail.com>
