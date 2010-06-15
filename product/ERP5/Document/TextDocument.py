# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
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

from AccessControl.ZopeGuards import guarded_getattr
from AccessControl import ClassSecurityInfo
from zLOG import LOG, WARNING
from Products.ERP5Type.Base import WorkflowMethod
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.utils import _setCacheHeaders, _ViewEmulator
from OFS.Image import Pdata
from Products.ERP5Type import Permissions, PropertySheet
from Products.ERP5.Document.Document import Document, ConversionError,\
                                            NotConvertedError
from Products.ERP5.Document.File import File
from Products.ERP5Type.WebDAVSupport import TextContent
import re
import md5
import cStringIO

# Mixin Import
from Products.ERP5.mixin.cached_convertable import CachedConvertableMixin
from Products.ERP5.mixin.base_convertable import BaseConvertableFileMixin
try:
  from string import Template
except ImportError:
  from Products.ERP5Type.patches.string import Template

DEFAULT_CONTENT_TYPE = 'text/html'
_MARKER = []

class TextDocument(CachedConvertableMixin, BaseConvertableFileMixin,
                                                            TextContent, File):
    """A TextDocument impletents IDocument, IFile, IBaseConvertable, ICachedconvertable
    and ITextConvertable
    """

    meta_type = 'ERP5 Text Document'
    portal_type = 'Text Document'
    add_permission = Permissions.AddPortalContent

    # Declarative security
    security = ClassSecurityInfo()
    security.declareObjectProtected(Permissions.AccessContentsInformation)

    # Declarative properties
    property_sheets = ( PropertySheet.Base
                      , PropertySheet.XMLObject
                      , PropertySheet.CategoryCore
                      , PropertySheet.DublinCore
                      , PropertySheet.Version
                      , PropertySheet.Document
                      , PropertySheet.Snapshot
                      , PropertySheet.ExternalDocument
                      , PropertySheet.Url
                      , PropertySheet.TextDocument
                      , PropertySheet.Data
                      , PropertySheet.Reference
                      )

    def _substituteTextContent(self, text, safe_substitute=True, **kw):
      # If a method for string substitutions of the text content, perform it.
      # Decode everything into unicode before the substitutions, in order to
      # avoid encoding errors.
      method_id = self.getTextContentSubstitutionMappingMethodId()
      if method_id:
        try:
          mapping = guarded_getattr(self, method_id)(**kw)
        except AttributeError:
          LOG('TextDocument', WARNING, 'could not get the substitution'
              ' mapping method %s from %r, so the content will not be'
              ' substituted.' % (method_id, self.getRelativeUrl()))
          return text

        is_str = isinstance(text, str)
        if is_str:
          text = text.decode('utf-8')

        unicode_mapping = {}
        for k, v in mapping.iteritems():
          if isinstance(v, str):
            v = v.decode('utf-8')
          elif not isinstance(v, unicode):
            v = str(v).decode('utf-8')
          unicode_mapping[k] = v

        if safe_substitute:
          text = Template(text).safe_substitute(unicode_mapping)
        else:
          text = Template(text).substitute(unicode_mapping)

        # If the original was a str, convert it back to str.
        if is_str:
          text = text.encode('utf-8')

      return text

    security.declareProtected(Permissions.View, 'asSubjectText')
    def asSubjectText(self, substitution_method_parameter_dict=None, safe_substitute=True, **kw):
      """
        Converts the subject of the document to a textual representation.
      """
      subject = TextDocument.inheritedAttribute('asSubjectText')(self, **kw)
      if substitution_method_parameter_dict is None:
        substitution_method_parameter_dict = {}
      return self._substituteTextContent(subject, safe_substitute=safe_substitute,
                                         **substitution_method_parameter_dict)

    def _convert(self, format, substitution_method_parameter_dict=None,
                safe_substitute=True, charset=None, text_content=None, **kw):
      """
        Convert text using portal_transforms or oood
      """
      src_mimetype = self.getContentType()
      if not format and src_mimetype == 'text/html':
        format = 'html' # Force safe_html
      if not format:
        # can return document without conversion
        return src_mimetype, self.getTextContent()
      portal = self.getPortalObject()
      mime_type = getToolByName(portal, 'mimetypes_registry').\
                                            lookupExtension('name.%s' % format)
      original_mime_type = mime_type = str(mime_type)
      if text_content is None:
        # check if document has set text_content and convert if necessary
        text_content = self.getTextContent()
      if text_content:
        kw['format'] = format
        if not self.hasConversion(**kw):
          portal_transforms = getToolByName(portal, 'portal_transforms')
          filename = self.getSourceReference(self.getTitleOrId())
          if mime_type == 'text/html':
            mime_type = 'text/x-html-safe'
          result = portal_transforms.convertToData(mime_type, text_content,
                                                   object=self, context=self,
                                                   filename=filename,
                                                   mimetype=src_mimetype,
                                                   encoding=charset)
          if result is None:
            raise ConversionError('TextDocument conversion error. '
                                  'portal_transforms failed to convert '\
                                  'to %s: %r' % (mime_type, self))
          self.setConversion(result, original_mime_type, **kw)
        else:
          mime_type, result = self.getConversion(**kw)
        if substitution_method_parameter_dict is None:
          substitution_method_parameter_dict = {}
        result = self._substituteTextContent(result, safe_substitute=safe_substitute,
                                             **substitution_method_parameter_dict)
        return original_mime_type, result
      else:
        # text_content is not set, return empty string instead of None
        return original_mime_type, ''

    def __call__(self):
      _setCacheHeaders(_ViewEmulator().__of__(self), {})
      return Document.__call__(self)

    security.declareProtected(Permissions.AccessContentsInformation, 'getContentBaseURL')
    def getContentBaseURL(self):
      """
        Returns the content base URL based on the actual content
        (in HTML)
      """
      if self.hasTextContent():
        html = self._asHTML()
        base_list = re.findall(self.base_parser, str(html))
        if base_list:
          return base_list[0]
      return Document.getContentBaseURL(self)

    security.declareProtected(Permissions.AccessContentsInformation, 'hasBaseData')
    def hasBaseData(self):
      """
        A TextDocument store its base_data in the "text_content" property.
        Having base_data is equivalent to having some text_content.
      """
      return self.hasTextContent()

    security.declareProtected(Permissions.ModifyPortalContent, 'setBaseData')
    def setBaseData(self, value):
      """Store base_data into text_content
      """
      self._setTextContent(value)

    security.declareProtected(Permissions.ModifyPortalContent, '_setBaseData')
    _setBaseData = setBaseData

    security.declareProtected(Permissions.ModifyPortalContent,
                                                            '_baseSetBaseData')
    _baseSetBaseData = _setBaseData

    security.declareProtected(Permissions.ModifyPortalContent,
                                                          'setBaseContentType')
    def setBaseContentType(self, value):
      """store value into content_type
      """
      self._setContentType(value)

    security.declareProtected(Permissions.ModifyPortalContent,
                                                         '_setBaseContentType')
    _setBaseContentType = setBaseContentType

    security.declareProtected(Permissions.ModifyPortalContent,
                                                     '_baseSetBaseContentType')
    _baseSetBaseContentType = _setBaseContentType

    security.declareProtected(Permissions.AccessContentsInformation,
                                                                 'getBaseData')
    def getBaseData(self, default=_MARKER):
      """
      """
      self._checkConversionFormatPermission(None)
      if default is _MARKER:
        return self.getTextContent()
      else:
        return self.getTextContent(default=default)

    security.declareProtected(Permissions.AccessContentsInformation,
                                                                 'hasBaseData')
    def hasBaseData(self):
      """
      """
      return self.hasTextContent()

    security.declareProtected(Permissions.AccessContentsInformation,
                                                              'getContentType')
    def getContentType(self, default=_MARKER):
      """Backward compatibility, read content_type
      from text_format property
      """
      if not self.hasContentType():
        # getProperty can not be used
        # because text_format is not registered in local_properties
        if default is _MARKER:
          return getattr(self, 'text_format', None)
        else:
          return getattr(self, 'text_format', default)
      else:
        if default is _MARKER:
          return self._baseGetContentType()
        else:
          return self._baseGetContentType(default)

    # base_convertable support
    security.declareProtected(Permissions.AccessContentsInformation,
                                                 'isSupportBaseDataConversion')
    def isSupportBaseDataConversion(self):
      """
      """
      return True

    def _convertToBaseFormat(self):
      """Conversion to base format for TextDocument consist
      to convert file content into utf-8
      """
      def guessCharsetAndConvert(document, text_content, content_type):
        """
        return encoded content_type and message if encoding
        is not utf-8
        """
        codec = document._guessEncoding(text_content, content_type)
        if codec is not None:
          try:
            text_content = text_content.decode(codec).encode('utf-8')
          except (UnicodeDecodeError, LookupError):
            message = 'Conversion to base format with codec %r fails' % codec
            # try again with another guesser based on file command
            codec = document._guessEncoding(text_content, 'text/plain')
            if codec is not None:
              try:
                text_content = text_content.decode(codec).encode('utf-8')
              except (UnicodeDecodeError, LookupError):
                message = 'Conversion to base format with codec %r fails'\
                                                                        % codec
              else:
                message = 'Conversion to base format with codec %r succeeds'\
                                                                        % codec
          else:
            message = 'Conversion to base format with codec %r succeeds'\
                                                                        % codec
        else:
          message = 'Conversion to base format without codec fails'
        return text_content, message

      content_type = self.getContentType() or DEFAULT_CONTENT_TYPE
      text_content = self.getData()
      if content_type == 'text/html':
        re_match = self.charset_parser.search(text_content)
        message = 'Conversion to base format succeeds'
        if re_match is not None:
          charset = re_match.group('charset')
          if charset.lower() != 'utf-8':
            try:
              # Use encoding in html document
              text_content = text_content.decode(charset).encode('utf-8')
            except (UnicodeDecodeError, LookupError):
              # Encoding read from document is wrong
              text_content, message = guessCharsetAndConvert(self,
                                                    text_content, content_type)
            else:
              message = 'Conversion to base format with charset %r succeeds'\
                                                                      % charset
              charset = 'utf-8' # Override charset if convertion succeeds
              # change charset value in html_document as well
              def subCharset(matchobj):
                keyword = matchobj.group('keyword')
                charset = matchobj.group('charset')
                if not (keyword or charset):
                  # no match, return same string
                  return matchobj.group(0)
                elif keyword:
                  # if keyword is present, replace charset just after
                  return keyword + 'utf-8'
              text_content = self.charset_parser.sub(subCharset, text_content)
        else:
          text_content, message = guessCharsetAndConvert(self,
                                                    text_content, content_type)
      else:
        # generaly text/plain
        try:
          # if succeeds, not need to change encoding
          # it's already utf-8
          text_content.decode('utf-8')
        except (UnicodeDecodeError, LookupError), error_message:
          text_content, message = guessCharsetAndConvert(self,
                                                    text_content, content_type)
        else:
          message = 'Conversion to base format succeeds'
      self._setBaseData(text_content)
      self._setBaseContentType(content_type)
      return message

    security.declareProtected(Permissions.AccessContentsInformation,
                                                              'getTextContent')
    def getTextContent(self, default=_MARKER):
      """Overriden method to check
      permission to access content in raw format
      """
      self._checkConversionFormatPermission(None)
      if default is _MARKER:
        return self._baseGetTextContent()
      else:
        return self._baseGetTextContent(default)

    # Backward compatibility for replacement of text_format by content_type
    security.declareProtected(Permissions.AccessContentsInformation,
                                                               'getTextFormat')
    def getTextFormat(self, default=_MARKER):
      """
      """
      LOG('TextDocument', WARNING,
                'Usage of text_format is deprecated, use text_content instead')
      return self.getContentType(default)

    security.declareProtected(Permissions.ModifyPortalContent, 'setTextFormat')
    def setTextFormat(self, value):
      """
      """
      LOG('TextDocument', WARNING,
                'Usage of text_format is deprecated, use text_content instead')
      return self.setContentType(value)

    security.declareProtected(Permissions.ModifyPortalContent,
                                                              '_setTextFormat')
    def _setTextFormat(self, value):
      """
      """
      LOG('TextDocument', WARNING,
                'Usage of text_format is deprecated, use text_content instead')
      return self._setContentType(value)
