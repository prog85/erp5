##############################################################################
#
# Copyright (c) 2009 Nexedi KK and Contributors. All Rights Reserved.
#                    Tatuya Kamada <tatuya@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################

import unittest
from threading import Thread
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from AccessControl.SecurityManagement import newSecurityManager
from Products.ERP5Form.Selection import Selection
from Products.ERP5Form.SelectionTool import SelectionTool
from Products.ERP5OOo.OOoUtils import OOoBuilder
from zLOG import LOG , INFO
import os

class TestFormPrintout(ERP5TypeTestCase):
  quiet = 1
  run_all_test = 1

  def getTitle(self):
    """
      Return the title of the current test set.
    """
    return "FormPrintout"

  def getBusinessTemplateList(self):
    return ('erp5_ui_test', 'erp5_odt_style')

  def afterSetUp(self):
    self.login()
    foo_file_path = os.path.join(os.path.dirname(__file__),
                                'test_document',
                                'Foo_001.odt')
    foo_file = open(foo_file_path, 'rb')
    custom = self.portal.portal_skins.custom
    addStyleSheet = custom.manage_addProduct['OFSP'].manage_addFile
    addStyleSheet(id='Foo_getODTStyleSheet', file=foo_file, title='',
                  precondition='', content_type = 'application/vnd.oasis.opendocument.text')
    erp5OOo = custom.manage_addProduct['ERP5OOo']
    addOOoTemplate = erp5OOo.addOOoTemplate
    addOOoTemplate(id='Foo_viewAsOdt', title='')
    request = self.app.REQUEST
    Foo_viewAsOdt = custom.Foo_viewAsOdt
    Foo_viewAsOdt.doSettings(request, title='', xml_file_id='content.xml',
                             ooo_stylesheet='Foo_getODTStyleSheet')
    #Foo_viewAsOdt.pt_upload(request, file=foo_file)
    #render_result = Foo_viewAsOdt(REQUEST=request)
    #LOG('testFormPrintout render_result:', INFO, render_result)
    builder = OOoBuilder(foo_file)
    content = builder.extract('content.xml')
    Foo_viewAsOdt.pt_edit(content, content_type='application/vnd.oasis.opendocument.text')

    erp5OOo.addFormPrintout(id='Foo_viewAsPrintout', title='',
                            form_name='Foo_view', template='Foo_getODTStyleSheet')

  def login(self):
    uf = self.getPortal().acl_users
    uf._doAddUser('tatuya', '', ['Manager'], [])
    user = uf.getUserById('tatuya').__of__(uf)
    newSecurityManager(None, user)
                          
  def _test_01_Paragraph(self, quiet=0, run=run_all_test):
    """
    mapping a field to a paragraph
    """
    portal = self.getPortal()
    foo_module = self.portal.foo_module
    if foo_module._getOb('test1', None) is None:
      foo_module.newContent(id='test1', portal_type='Foo')
    test1 =  foo_module.test1
    test1.setTitle('Foo title!')
    get_transaction().commit()
    self.tic()

    # test target
    foo_printout = portal.foo_module.test1.Foo_viewAsPrintout

    request = self.app.REQUEST
    # 1. Normal case: "my_title" field to the "my_title" reference in the ODF document
    self.portal.changeSkin('ODT')
    odf_document = foo_printout.index_html(REQUEST=request)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertTrue(content_xml.find("Foo title!") > 0)

    # 2. Normal case: change the field value and check again the ODF document
    test1.setTitle("Changed Title!")
    #foo_form.my_title.set_value('default', "Changed Title!")
    odf_document = foo_printout.index_html(REQUEST=request)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertTrue(content_xml.find("Changed Title!") > 0)

    # 3. False case: change the field name 
    test1.setTitle("you cannot find")
    # rename id 'my_title' to 'xxx_title', then does not match in the ODF document
    foo_form = portal.foo_module.test1.Foo_view
    foo_form.manage_renameObject('my_title', 'xxx_title', REQUEST=request)
    odf_document = foo_printout.index_html(REQUEST=request)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertFalse(content_xml.find("you cannot find") > 0)
    # put back
    foo_form.manage_renameObject('xxx_title', 'my_title', REQUEST=request)

    ## 4. False case: does not set a ODF template
    self.assertTrue(foo_printout.template == 'Foo_getODTStyleSheet')
    foo_printout.template = None
    # template == None, causes a ValueError 
    try: 
      foo_printout.index_html(REQUEST=request)
    except ValueError, e:
      # e -> 'Can not create a ODF Document without a odf_template'
      self.assertTrue(True)


  def test_02_Table(self, quiet=0, run=run_all_test):
    """
    To test mapping a listbox(Form) to a table(ODF)
    """
    portal = self.getPortal()
    ## append 'test1' data to a listbox
    foo_module = self.portal.foo_module
    if foo_module._getOb('test1', None) is None:
      foo_module.newContent(id='test1', portal_type='Foo')
    test1 =  foo_module.test1
    if test1._getOb("foo_1", None) is None:
      test1.newContent("foo_1", portal_type='Foo Line')
    get_transaction().commit()
    self.tic()
    # test target
    foo_printout = portal.foo_module.test1.Foo_viewAsPrintout

    # Test Data format
    #
    # * ODF table named 'listbox':
    # +------------------------------+
    # |  ID | Title | Quantity |Date |
    # |-----+-------+----------+-----|
    # |     |       |          |     |
    # |-----+-------+----------+-----|
    # |   Total     |          |     |
    # +------------------------------+
    #
    # * ODF table named 'listbox2':
    # +-------------------------------+
    # |  A    |   B   |   C   |   D   |
    # |-------+-------+-------+-------|
    # |       |       |       |       |
    # +-------+-------+-------+-------+
    #
    # * ODF table named 'listbox3':
    # the table listbox3 has not table header.
    # first row is table content, too.
    # +-------------------------------+
    # |  1    |   2   |   3   |   4   |
    # |-------+-------+-------+-------|
    # |       |       |       |       |
    # +-------+-------+-------+-------+
    # 

    # 1. Normal Case: ODF table last row is stat line
    test1.foo_1.setTitle('foo_title_1')
    foo_form = test1.Foo_view
    listbox = foo_form.listbox
    request = self.app.REQUEST 
    request['here'] = test1
    listboxline_list = listbox.get_value('default', render_format = 'list',
                                         REQUEST = request)
    self.assertEqual(len(listboxline_list), 3)
    self.assertTrue(listboxline_list[0].isTitleLine())
    self.assertTrue(listboxline_list[1].isDataLine())
    self.assertTrue(listboxline_list[2].isStatLine())
    column_list = listboxline_list[0].getColumnPropertyList()
    self.assertEqual(len(column_list), 4)
    self.assertTrue(listboxline_list[1].getColumnProperty('id') == "foo_1")
    self.assertTrue(listboxline_list[1].getColumnProperty('title') == "foo_title_1")
    
    odf_document = foo_printout.index_html(REQUEST=request)
    #test_output = open("/tmp/test_02_01_Table.odf", "w")
    #test_output.write(odf_document)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertTrue(content_xml.find("foo_title_1") > 0)

    # 2. Irregular case: listbox columns count smaller than table columns count
    test1.foo_1.setTitle('foo_title_2')
    message = listbox.ListBox_setPropertyList(
      field_list_method = 'objectValues',
      field_portal_types = 'Foo Line | Foo Line',
      field_stat_method = 'portal_catalog',
      field_stat_columns = 'quantity | Foo_statQuantity',
      field_columns = 'id|ID\ntitle|Title\nquantity|Quantity',)
    self.failUnless('Set Successfully' in message)
    self.assertEqual(listbox.get_value('columns'),
                     [('id', 'ID'), ('title', 'Title'), ('quantity', 'Quantity')])
    listboxline_list = listbox.get_value('default', render_format = 'list',
                                         REQUEST = request)
    self.assertEqual(len(listboxline_list), 3)
    self.assertTrue(listboxline_list[0].isTitleLine())
    self.assertTrue(listboxline_list[1].isDataLine())
    self.assertTrue(listboxline_list[2].isStatLine())
    self.assertTrue(listboxline_list[1].getColumnProperty('title') == "foo_title_2")
    
    column_list = listboxline_list[0].getColumnPropertyList()
    self.assertEqual(len(column_list), 3)

    odf_document = foo_printout.index_html(REQUEST=request)
    #test_output = open("/tmp/test_02_02_Table.odf", "w")
    #test_output.write(odf_document)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertFalse(content_xml.find("foo_title_1") > 0)
    self.assertTrue(content_xml.find("foo_title_2") > 0)

    # 3. Irregular case: listbox columns count larger than table columns count
    test1.foo_1.setTitle('foo_title_3')
    message = listbox.ListBox_setPropertyList(
      field_list_method = 'objectValues',
      field_portal_types = 'Foo Line | Foo Line',
      field_stat_method = 'portal_catalog',
      field_stat_columns = 'quantity | Foo_statQuantity',
      field_columns = 'id|ID\ntitle|Title\nquantity|Quantity\n'
                      'start_date|Date\nstatus|Status',)
    self.failUnless('Set Successfully' in message)
    listboxline_list = listbox.get_value('default', render_format = 'list',
                                         REQUEST = request)
    self.assertEqual(len(listboxline_list), 3)
    self.assertTrue(listboxline_list[1].getColumnProperty('title') == "foo_title_3")
    
    column_list = listboxline_list[0].getColumnPropertyList()
    self.assertEqual(len(column_list), 5)
    odf_document = foo_printout.index_html(REQUEST=request)
    LOG('testFormPrintout', INFO, 'content:%s' % content_xml)
    #test_output = open("/tmp/test_02_03_Table.odf", "w")
    #test_output.write(odf_document)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertFalse(content_xml.find("foo_title_2") > 0)
    self.assertTrue(content_xml.find("foo_title_3") > 0)

    # 4. Irregular case: listbox have not a stat line, but table has a stat line
    if test1._getOb("foo_2", None) is None:
      test1.newContent("foo_2", portal_type='Foo Line')
    get_transaction().commit()
    self.tic()

    test1.foo_1.setTitle('foo_title_4')
    message = listbox.ListBox_setPropertyList(
      field_list_method = 'objectValues',
      field_portal_types = 'Foo Line | Foo Line',
      field_stat_method = '',
      field_stat_columns = 'quantity | Foo_statQuantity',
      field_columns = 'id|ID\ntitle|Title\nquantity|Quantity\nstart_date|Date',)
    self.failUnless('Set Successfully' in message)
    listboxline_list = listbox.get_value('default', render_format = 'list',
                                         REQUEST = request)
    for line in listboxline_list:
      self.assertEqual(line.isStatLine(), False)
    self.assertEqual(len(listboxline_list), 3)
    self.assertTrue(listboxline_list[1].getColumnProperty('title') == "foo_title_4")

    odf_document = foo_printout.index_html(REQUEST=request)
    #test_output = open("/tmp/test_02_04_Table.odf", "w")
    #test_output.write(odf_document)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertTrue(odf_document is not None)
    self.assertFalse(content_xml.find("foo_title_3") > 0)
    self.assertTrue(content_xml.find("foo_title_4") > 0)

    # 5. Normal case: the listobx of a form and the ODF table are same layout
    foo_form.manage_renameObject('listbox', 'listbox2', REQUEST=request)
    listbox2 = foo_form.listbox2
    test1.foo_1.setTitle('foo_title_5')
    message = listbox2.ListBox_setPropertyList(
      field_list_method = 'objectValues',
      field_portal_types = 'Foo Line | Foo Line',
      field_stat_method = 'portal_catalog',
      field_stat_columns = 'quantity | Foo_statQuantity',
      field_columns = 'id|ID\ntitle|Title\nquantity|Quantity\nstart_date|Date',)
    self.failUnless('Set Successfully' in message)
    listboxline_list = listbox2.get_value('default', render_format = 'list',
                                         REQUEST = request)
    self.assertEqual(len(listboxline_list), 4)
    self.assertTrue(listboxline_list[1].getColumnProperty('title') == "foo_title_5")

    odf_document = foo_printout.index_html(REQUEST=request)
    #test_output = open("/tmp/test_02_05_Table.odf", "w")
    #test_output.write(odf_document)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertFalse(content_xml.find("foo_title_4") > 0)
    self.assertTrue(content_xml.find("foo_title_5") > 0)
    
    # put back the field name
    foo_form.manage_renameObject('listbox2', 'listbox', REQUEST=request)

    # 6. Normal case: ODF table does not have a header
    foo_form.manage_renameObject('listbox', 'listbox3', REQUEST=request)
    listbox3 = foo_form.listbox3
    test1.foo_1.setTitle('foo_title_6')
    listboxline_list = listbox3.get_value('default', render_format = 'list',
                                         REQUEST = request)
    self.assertEqual(len(listboxline_list), 4)
    self.assertTrue(listboxline_list[1].getColumnProperty('title') == "foo_title_6")

    odf_document = foo_printout.index_html(REQUEST=request)
    #test_output = open("/tmp/test_02_06_Table.odf", "w")
    #test_output.write(odf_document)
    self.assertTrue(odf_document is not None)
    builder = OOoBuilder(odf_document)
    content_xml = builder.extract("content.xml")
    self.assertFalse(content_xml.find("foo_title_5") > 0)
    self.assertTrue(content_xml.find("foo_title_6") > 0)

    # put back the field name
    foo_form.manage_renameObject('listbox3', 'listbox', REQUEST=request)

  def _test_03_Frame(self, quiet=0, run=run_all_test):
    """
    Frame not supported yet
    """
    pass

  def _test_04_Iteration(self, quiet=0, run=run_all_test):
    """
    Iteration(ReportSection) not supported yet.
    Probably to support *ReportBox* would be better.
    """
    pass

  def _test_05_Styles(self, quiet=0, run=run_all_test):
    """
    styles.xml not supported yet
    """
    pass

  def _test_06_Meta(self, quiet=0, run=run_all_test):
    """
    meta.xml not supported yet
    """
    pass
