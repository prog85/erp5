##############################################################################
#
# Copyright (c) 2010 Nexedi SARL and Contributors. All Rights Reserved.
#                    Arnaud Fontaine <arnaud.fontaine@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from AccessControl import ClassSecurityInfo

from Products.ERP5Type import Permissions, PropertySheet
from Products.ERP5Type.XMLObject import XMLObject

class StandardProperty(XMLObject):
  """
  Define an Acquired Property Document for a web-based Property Sheet
  """
  meta_type = 'ERP5 Standard Property'
  portal_type = 'Standard Property'

  # Declarative security
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)

  property_sheets = (PropertySheet.SimpleItem,
                     PropertySheet.StandardProperty,
                     PropertySheet.TranslatableProperty)

  # Names mapping between filesystem to web-based property, only
  # meaningful when importing a property from its filesystem
  # definition
  _name_mapping_filesystem_to_web_dict = {'id': 'reference',
                                          'type': 'elementary_type',
                                          'default': 'property_default'}

  security.declareProtected(Permissions.AccessContentsInformation,
                            'exportToFilesystemDefinition')
  def exportToFilesystemDefinition(self):
    """
    Return the filesystem definition of this web-based property
    """
    return {'id': self.getReference(),
            'description': self.getDescription(),
            'type': self.getElementaryType(),
            'storage_id': self.getStorageId(),
            'multivalued': self.getMultivalued(),
            'default': self.getPropertyDefault(),
            'range': self.getRange(),
            'preference': self.getPreference(),
            'read_permission': self.getReadPermission(),
            'write_permission': self.getWritePermission(),
            'translatable': self.getTranslatable(),
            'translation_domain': self.getTranslationDomain()}

  def _convertFromFilesytemPropertyDict(self, filesystem_property_dict):
    """
    Convert a property dict coming from a Property Sheet on the
    filesystem to a web-based property dict
    """
    # Prepare a dictionnary of the web-based property
    web_property_dict = {}

    for fs_property_name, value in filesystem_property_dict.iteritems():
      # Convert filesystem property name to web-based if necessary
      web_property_name = \
          fs_property_name in self._name_mapping_filesystem_to_web_dict and \
          self._name_mapping_filesystem_to_web_dict[fs_property_name] or \
          fs_property_name

      web_property_dict[web_property_name] = value

    return web_property_dict

  security.declareProtected(Permissions.AccessContentsInformation,
                            'importFromFilesystemDefinition')
  def importFromFilesystemDefinition(self, filesystem_property_dict):
    """
    Set attributes from the filesystem definition of a property
    """
    self.edit(**self._convertFromFilesytemPropertyDict(filesystem_property_dict))
