import pygame
from pygame.locals import *
from numpy import *

import common
from game import game
from player import BasePlayer
from field import Castle, Field


class PlacePlayer(BasePlayer):

    cantbuild_pic = common.load_image("cantbuild.png", alpha=True)

    def __init__(self, player):
        BasePlayer.__init__(self)
        self.player = player

    def init(self):
        BasePlayer.init(self)
        (self.pos, secured_fields) = self.player.get_center_and_field_count()
        self.new_cannons = secured_fields // 300
        for castle in game.field.map.castles:
            if self.player.secured[castle.pos]:
                if castle.big:
                    self.new_cannons += 2
                    # print self.player, castle.pos, self.new_cannons, castle
                else:
                    self.new_cannons += 1
        if not self.player.alive:
            self.new_cannons = 0
        self.selected_type = 0

    def draw_cursor(self):
        if not self.new_cannons:
            return
        from cannon import Cannon

        common.blit(
            Cannon.cannon_pic[self.selected_type][0],
            (self.pos[0] * common.block_size, self.pos[1] * common.block_size),
        )

        for offset in common.coords((2 + self.selected_type,) * 2):
            pos = tuple(add(self.pos, offset))
            if game.field.array[pos] != Field.EMPTY or self.player.secured[pos] == 0:
                common.blit(self.cantbuild_pic, multiply(pos, common.block_size))

        # draw number of remaining cannons above cursor
        surface = common.font.render(str(self.new_cannons), True, (0, 0, 0))
        text_pos = multiply(self.pos, common.block_size)
        text_pos[0] += 12 + common.block_size / 2 * self.selected_type
        text_pos[1] += common.block_size / 2 * self.selected_type
        common.blit(surface, text_pos)

    def place_cannon(self):
        from cannon import Cannon

        price = Cannon.price[self.selected_type]
        if self.new_cannons < price:
            raise common.ActionNotPossible
        can = Cannon(self.pos, self.player, self.selected_type)
        can.backbuffer_blit()
        self.new_cannons -= price
        if self.new_cannons < Cannon.price[self.selected_type]:
            self.selected_type = 0

    def change_type(self):
        self.selected_type += 1
        self.selected_type %= 2
        from cannon import Cannon

        if self.new_cannons < Cannon.price[self.selected_type]:
            self.selected_type = 0

    def handle_event(self, event):
        try:
            if self.new_cannons:
                self.handle_build_or_place_event(
                    event, (self.place_cannon, self.change_type), self.pos
                )
        except common.ActionNotPossible:
            pass

    def handle_movement(self, passed_milliseconds):
        pass

    def move(self, vector):
        for i in (0, 1):
            newpos = self.pos[i] + vector[i]
            if newpos != common.bound(newpos, 0, common.field_size[i] - 2):
                raise common.ActionNotPossible
            else:
                self.pos[i] = newpos


from network import ServerObject, ClientObject, networkify


class PlacePlayerServer(ServerObject, PlacePlayer):
    def get_state(self):
        return {"player": self.player}


class PlacePlayerClient(ClientObject, PlacePlayer):
    def set_state(self, state):
        self.__dict__ = state
        BasePlayer.__init__(self)


networkify(
    cacheable=PlacePlayerServer,
    remote_cache=PlacePlayerClient,
    implementation=PlacePlayer,
    method_names=("move", "change_type", "place_cannon"),
)
