from Products.ERP5Type.Base import Base 

def getAllBaseClassList(portal_type):
  """ returns all base classes."""
  types_tool = portal_type.getParent()
  module_class = types_tool.getPortalTypeClass(portal_type.getId())
  module_class.loadClass()
  return [clz for clz in module_class.mro() if issubclass(clz, Base)]

def getAllBaseClassNameList(portal_type):
  """ returns all base class names."""
  base_class_list = getAllBaseClassList(portal_type)
  return [base_class.__name__.replace(' ', '') for base_class in base_class_list]