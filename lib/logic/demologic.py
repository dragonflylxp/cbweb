#!/usr/bin/env python
# encoding: utf-8

import traceback
from logic.dbs import BaseModel, access


class DemoLogic(BaseModel):

    @access("r")
    def demoselect(self, tablename):
        ret = {}
        try:
            sql = "SELECT * FROM {} LIMIT 1".format(tablename)
            self.cursor.execute(sql)
            ret = self.cursor.fetchone()
        except:
            logger.error(traceback.format_exc())
        finally:
            ret

    @access("w")
    def demoupdte(self, tablename, field, value):
        try:
            sql = "UPDATE {} SET {}={}".format(tablename, field, value)
            self.cursor.execute(sql)
            self.commit()
        except:
            self.rollback()
            logger.error(traceback.format_exc())
