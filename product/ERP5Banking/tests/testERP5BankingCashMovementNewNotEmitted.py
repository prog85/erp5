##############################################################################
#
# Copyright (c) 2007 Nexedi SARL and Convault_destinationbutors. All Rights Reserved.
#                    Aurelien Calonne <aurel@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redisvault_destinationbute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is disvault_destinationbuted in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################


# import requested python module
import os
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.DCWorkflow.DCWorkflow import Unauthorized, ValidationFailed
from Products.ERP5Banking.tests.testERP5BankingMonetaryIssue import TestERP5BankingMonetaryReceptionMixin
from DateTime import DateTime

# Needed in order to have a log file inside the current folder
os.environ['EVENT_LOG_FILE']     = os.path.join(os.getcwd(), 'zLOG.log')
# Define the level of log we want, here is all
os.environ['EVENT_LOG_SEVERITY'] = '-300'

class TestERP5BankingCashMovementNewNotEmitted(TestERP5BankingMonetaryReceptionMixin):
  """
    This class is a unit test to check the module of Cash Movement New Not Emitted
  """


  # pseudo constants
  RUN_ALL_TEST = 1 # we want to run all test
  QUIET = 0 # we don't want the test to be quiet

  def getTitle(self):
    """
      Return the title of the test
    """
    return "ERP5BankingCashMovementNewNotEmitted"

  def getCashMovementModule(self):
    return getattr(self.getPortal(), 'cash_movement_new_not_emitted_module')

  def getMonetaryReceptionModule(self):
    return getattr(self.getPortal(), 'monetary_reception_module')

  def afterSetUp(self):
    """
      Method called before the launch of the test to initialize some data
    """
    # Set some variables :
    self.initDefaultVariable()
    # the cahs transfer module
    self.cash_movement_module = self.getCashMovementModule()
    self.monetary_reception_module = self.getMonetaryReceptionModule()
    self.createManagerAndLogin()
    self.current_date = DateTime()
    # create categories
    sites = self.createFunctionGroupSiteCategory(site_list=[
        ('france', 'P00', 'testsite/principale'),
        ('spain', 'S00', 'testsite/principale'),
    ])
    self.france, self.spain = sites[-2:]

    # Before the test, we need to input the inventory

    self.vault_source = self.france.caveau.serre.encaisse_des_billets_neufs_non_emis_en_transit_allant_a.spain
    self.vault_destination = self.spain.caveau.serre.encaisse_des_billets_neufs_non_emis
    self.reception_site = self.reception = self.vault_source
    self.destination_site = self.vault_destination
    # Create an Organisation that will be used for users assignment
    self.checkUserFolderType()
    self.organisation = self.organisation_module.newContent(id='baobab_org', portal_type='Organisation',
                          function='banking', group='baobab',
                          site='testsite/principale/france')
    # define the user
    user_dict = {
        'super_user' : [['Manager'], self.organisation, 'banking/comptable',
            'baobab', 'testsite/principale/france/surface/banque_interne/guichet_1']
      }
    # call method to create this user
    self.createERP5Users(user_dict)
    self.logout()
    self.login('super_user')
    self.openCounterDate(site=self.france)
    self.openCounterDate(site=self.spain, id='counter_date_2')

  def stepCheckObjects(self, sequence=None, sequence_list=None, **kwd):
    self.checkResourceCreated()
    self.assertEqual(self.cash_movement_module.getPortalType(), 'Cash Movement New Not Emitted Module')
    self.assertEqual(len(self.cash_movement_module.objectValues()), 0)

  def stepCreateCashMovement(self, sequence=None, sequence_list=None, 
                             none_destination=0, **kwd):
    self.cash_movement = self.cash_movement_module.newContent(
      id='cash_movement_1',
      portal_type='Cash Movement New Not Emitted', 
      source=self.vault_source.getRelativeUrl(),
      destination_section_value=self.spain,
      description='test',
      start_date=self.date,
      source_total_asset_price=2000000.0)
    self.stepTic()
    self.assertEqual(len(self.cash_movement_module.objectValues()), 1)
    self.cash_movement = getattr(self.cash_movement_module, 'cash_movement_1')
    self.assertEqual(self.cash_movement.getPortalType(), 'Cash Movement New Not Emitted')
    self.assertEqual(self.cash_movement.getDestinationSection(),
            'site/testsite/principale/spain')
    self.assertEqual(self.cash_movement.getBaobabSource(),
            'site/testsite/principale/france/caveau/serre/encaisse_des_billets_neufs_non_emis_en_transit_allant_a/spain')
    self.setDocumentSourceReference(self.cash_movement)


  def stepCreateCashContainer(self, sequence=None, sequence_list=None, **kwd):
    """
    Create the cash container
    """
    # get the cash container item from the monetary reception
    cash_container_item_list = [x.getObject() for x in self.simulation_tool.getCurrentTrackingList(node=self.reception.getRelativeUrl())]
    self.assertEqual(len(cash_container_item_list), 2)
    def reference_sort(a,b):
      return cmp(a.getReference(),b.getReference())
    cash_container_item_list.sort(reference_sort)

    # contruct list of dict to create cash container
    new_cash_container_list = []
    i = 1
    for cash_container in cash_container_item_list:
      # register cash container on self to check aggregate value later
      setattr(self, 'cash_container_item_%s' %(str(i),), cash_container)
      container_dict = {}
      container_dict['id'] = str(i)
      container_dict['reference'] = cash_container.getReference()
      container_dict['range_start'] = cash_container.getCashNumberRangeStart()
      container_dict['range_stop'] = cash_container.getCashNumberRangeStop()
      cash_container_line = cash_container.objectValues()[0]
      container_dict['quantity'] = cash_container_line.getQuantity()
      container_dict['aggregate'] = cash_container
      new_cash_container_list.append(container_dict)
      i+=1
      
    def reference_sort(a,b):
      return cmp(a['reference'],b['reference'])
    new_cash_container_list.sort(reference_sort)

    global_dict = {}
    global_dict['emission_letter'] = 'p'
    global_dict['variation'] = '2003'
    global_dict['cash_status'] = 'new_not_emitted'
    global_dict['resource'] = self.billet_10000

    self.createCashContainer(self.cash_movement, 'Cash Movement New Not Emitted Container', global_dict, new_cash_container_list, 'Cash Movement New Not Emitted Line')

    self.stepTic()
    self.assertEqual(len(self.cash_movement.objectValues()), 3)
    self.assertEqual(self.cash_movement.getBaobabDestination(),
            'site/testsite/principale/spain/caveau/serre/encaisse_des_billets_neufs_non_emis')

  def stepStopDocument(self, sequence=None, sequence_list=None, **kwd):
    """
    Stop the cash_movement and check it
    """
    self.workflow_tool.doActionFor(self.cash_movement, 'stop_action',
                  wf_id='cash_movement_new_not_emitted_workflow', stop_date=self.date)
    self.stepTic()
    state = self.cash_movement.getSimulationState()
    self.assertEqual(state, 'stopped')

  def stepConfirmDocument(self, sequence=None, sequence_list=None, **kwd):
    """
    Confirm the cash_movement and check it
    """
    self.workflow_tool.doActionFor(self.cash_movement, 'confirm_action', wf_id='cash_movement_new_not_emitted_workflow')
    self.stepTic()
    state = self.cash_movement.getSimulationState()
    self.assertEqual(state, 'confirmed')

  def stepStartDocument(self, sequence=None, sequence_list=None, **kwd):
    """
    Start the cash_movement and check it
    """
    self.workflow_tool.doActionFor(self.cash_movement, 'start_action', wf_id='cash_movement_new_not_emitted_workflow')
    self.stepTic()
    state = self.cash_movement.getSimulationState()
    self.assertEqual(state, 'started')

  def stepDeliverDocument(self, sequence=None, sequence_list=None, **kwd):
    """
    Deliver the cash_movement with a good user
    and check that the deliver of a cash tranfer have achieved
    """
    self.workflow_tool.doActionFor(self.cash_movement, 'deliver_action', wf_id='cash_movement_new_not_emitted_workflow')
    self.stepTic()
    state = self.cash_movement.getSimulationState()
    self.assertEqual(state, 'delivered')

  def stepCheckCashDeliveryLine(self, sequence=None, sequence_list=None):
    """
    Check the cash delivery line
    """
    self.valid_line_1 = getattr(self.cash_movement, 'movement')
    self.assertEqual(self.valid_line_1.getPortalType(), 'Cash Movement New Not Emitted Line')
    self.assertEqual(self.valid_line_1.getResourceValue(), self.billet_10000)
    self.assertEqual(self.valid_line_1.getPrice(), 10000.0)
    self.assertEqual(self.valid_line_1.getQuantityUnit(), 'unit')
    self.assertEqual(self.valid_line_1.getBaobabDestinationVariationText(), 'cash_status/new_not_emitted\nemission_letter/p\nvariation/2003')
    self.assertEqual(len(self.valid_line_1.objectValues()), 1)
    variation = 'variation/2003'
    cell = self.valid_line_1.getCell('emission_letter/p', variation, 'cash_status/new_not_emitted')
    self.assertEqual(cell.getPortalType(), 'Cash Delivery Cell')
    self.assertEqual(cell.getResourceValue(), self.billet_10000)
    self.assertEqual(cell.getBaobabSourceValue(), self.vault_source)
    self.assertEqual(cell.getBaobabDestinationValue(), self.vault_destination)
    self.assertEqual(cell.getQuantity(), 200.0)


  def stepCheckCashContainer1(self, sequence=None, sequence_list=None):
    """
    Check the cash container
    """
    # check the cash delivery line
    self.container_1 = getattr(self.cash_movement, '1')
    # check its portal type
    self.assertEqual(self.container_1.getPortalType(), 'Cash Movement New Not Emitted Container')
    self.assertEqual(self.container_1.getReference(), 'unit_test_1')
    self.assertEqual(self.container_1.getCashNumberRangeStart(), '0')
    self.assertEqual(self.container_1.getCashNumberRangeStop(), '100')
    self.assertEqual(len(self.container_1.getAggregateValueList()), 1)
    self.assertEqual(self.container_1.getAggregateValueList()[0], self.cash_container_item_1)
#    self.failUnless(self.container_1.getAggregateValueList()[0] == self.cash_container_item_1 or self.container_1.getAggregateValueList()[0] == self.cash_container_item_2)
    self.assertEqual(len(self.container_1.objectIds()), 1)
    # now get the line and check it
    self.container_line_1 = self.container_1.objectValues()[0]
    self.assertEqual(self.container_line_1.getPortalType(), 'Container Line')
    # check the resource is banknotes of 10000
    self.assertEqual(self.container_line_1.getResourceValue(), self.billet_10000)
    # check we have one delivery cells
    self.assertEqual(len(self.container_1.objectValues()), 1)
    # now check for variation 2003
    cell = self.container_line_1.objectValues()[0]
    # chek portal types
    self.assertEqual(cell.getPortalType(), 'Container Cell')
    # check the banknote of the cell is banknote of 10000
    self.assertEqual(cell.getResourceValue(), self.billet_10000)
    # chek the value of the banknote
    self.assertEqual(cell.getPrice(), 10000.0)
    # check the source vault is caisse_1
    self.assertEqual(cell.getBaobabSourceValue(), self.vault_source)
    # check the destination vault is caisse_2
    self.assertEqual(cell.getBaobabDestinationValue(), self.vault_destination)
    self.assertEqual(cell.getQuantity(), 100.0)


  def stepCheckCashContainer2(self, sequence=None, sequence_list=None):
    """
    Check the cash container
    """
    # check the cash delivery line
    self.container_2 = getattr(self.cash_movement, '2')
    # check its portal type
    self.assertEqual(self.container_2.getPortalType(), 'Cash Movement New Not Emitted Container')
    self.assertEqual(self.container_2.getReference(), 'unit_test_2')
    self.assertEqual(self.container_2.getCashNumberRangeStart(), '100')
    self.assertEqual(self.container_2.getCashNumberRangeStop(), '200')
    self.assertEqual(len(self.container_2.getAggregateValueList()), 1)
    self.assertEqual(self.container_2.getAggregateValueList()[0], self.cash_container_item_2)
#    self.failUnless(self.container_2.getAggregateValueList()[0] == self.cash_container_item_2 or self.container_2.getAggregateValueList()[0] == self.cash_container_item_1)
    self.assertEqual(len(self.container_2.objectIds()), 1)
    # now get the line and check it
    self.container_line_2 = self.container_2.objectValues()[0]
    self.assertEqual(self.container_line_2.getPortalType(), 'Container Line')
    # check the resource is banknotes of 10000
    self.assertEqual(self.container_line_2.getResourceValue(), self.billet_10000)
    # check we have one delivery cells
    self.assertEqual(len(self.container_2.objectValues()), 1)
    # now check for variation 2003
    cell = self.container_line_2.objectValues()[0]
    # chek portal types
    self.assertEqual(cell.getPortalType(), 'Container Cell')
    # check the banknote of the cell is banknote of 10000
    self.assertEqual(cell.getResourceValue(), self.billet_10000)
    # chek the value of the banknote
    self.assertEqual(cell.getPrice(), 10000.0)
    # check the source vault is caisse_1
    self.assertEqual(cell.getBaobabSourceValue(), self.vault_source)
    self.assertEqual(cell.getBaobabDestinationValue(), self.vault_destination)
    self.assertEqual(cell.getQuantity(), 100.0)


  def stepCheckFinalInventory(self, sequence=None, sequence_list=None, **kwd):
    """
    Check that compution of inventory at vault caisse_2 is right after confirm and before deliver
    """
    # check source
    self.assertEqual(self.simulation_tool.getCurrentInventory(node=self.reception.getRelativeUrl(),
                                                              resource = self.billet_10000.getRelativeUrl()), 0.0)
    self.assertEqual(self.simulation_tool.getFutureInventory(node=self.reception.getRelativeUrl(),
                                                             resource = self.billet_10000.getRelativeUrl()), 0.0)
    # check destination
    self.assertEqual(self.simulation_tool.getCurrentInventory(node=self.vault_destination.getRelativeUrl(),
                                                              resource = self.billet_10000.getRelativeUrl()), 200.0)
    self.assertEqual(self.simulation_tool.getFutureInventory(node=self.vault_destination.getRelativeUrl(),
                                                             resource = self.billet_10000.getRelativeUrl()), 200.0)

  def stepCheckFinalContainerInventory(self, sequence=None, sequence_list=None, **kw):
    """
    Check cash container in item table
    """
    self.assertEqual(len(self.simulation_tool.getCurrentTrackingList(at_date=self.current_date, node=self.reception.getRelativeUrl())), 2)
    self.assertEqual(len(self.simulation_tool.getFutureTrackingList(at_date=self.current_date, node=self.reception.getRelativeUrl())), 2)

  def test_01_ERP5BankingCashMovementNewNotEmitted(self, quiet=QUIET, run=RUN_ALL_TEST):
    """
    Define the sequence of step that will be play
    """
    if not run: return
    sequence_list = SequenceList()
    # define the sequence
    
    
    sequence_string = 'Tic CheckObjects ' \
                      + 'CreateMonetaryReception Tic ' \
                      + 'CheckInitialInventory CheckInitialContainerInventory ' \
                      + 'CreateCashMovement Tic ' \
                      + 'CreateCashContainer Tic ' \
                      + 'CheckCashDeliveryLine ' \
                      + 'CheckCashContainer1 CheckCashContainer2 ' \
                      + 'ConfirmDocument Tic ' \
                      + 'StartDocument Tic ' \
                      + 'StopDocument Tic ' \
                      + 'DeliverDocument Tic ' \
                      + 'CheckFinalInventory CheckFinalContainerInventory'
                      
    
    sequence_list.addSequenceString(sequence_string)

    # play the sequence
    sequence_list.play(self)
